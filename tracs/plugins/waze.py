
from re import match
from typing import Any
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from click import echo
from csv import field_size_limit
from csv import reader as csv_reader
from datetime import datetime
from dateutil.tz import UTC
from dateutil.tz import gettz
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrack
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXTrackSegment
from logging import getLogger
from orjson import loads as load_json
from pathlib import Path

from . import document
from . import service
from .plugin import Plugin
from ..activity_types import ActivityTypes
from ..activity import Activity
from ..activity import Resource
from ..config import ApplicationState as state
from ..config import GlobalConfig as gc
from ..config import KEY_CLASSIFER
from ..config import KEY_METADATA
from ..config import KEY_PLUGINS
from ..config import KEY_RAW
from ..config import KEY_RESOURCES
from ..service import Service
from ..utils import as_datetime
from ..utils import to_isotime

log = getLogger( __name__ )

TAKEOUTS_DIRNAME = 'takeouts'
ACTIVITY_FILE = 'account_activity_3.csv'
SERVICE_NAME = 'waze'
DISPLAY_NAME = 'Waze'

@document
class WazeActivity( Activity ):

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.raw and len( self.raw ) > 0:
			if type( self.raw ) is dict: # todo: for backward compatibility
				self.raw_id = self.raw.get( 'id' )
				self.time = to_isotime( self.raw.get( 'time' ) )
				self.localtime = as_datetime( self.time, tz=gettz() )
			else:
				self.raw_id = int( self.raw[0][0].strftime( '%Y%m%d%H%M%S' ) )
				self.time = self.raw[0][0]
				self.localtime = as_datetime( self.time, tz=gettz() )

		self.type = ActivityTypes.drive
		self.classifier = SERVICE_NAME
		self.uid = f'{SERVICE_NAME}:{self.raw_id}'

@service
class Waze( Service, Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self._logged_in = True

	@property
	def _takeouts_dir( self ) -> Path:
		return Path( gc.db_dir, self.name, TAKEOUTS_DIRNAME )

	def path_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path for an activity.

		:param a: activity for which the path shall be calculated
		:param ext: file extension
		:return: path for activity
		"""
		id = str( a.raw_id )
		path = Path( gc.db_dir, self.name, id[0:4], id[4:6], id[6:8], id )
		if ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def login( self ) -> bool:
		return self._logged_in

	def _fetch( self, year: int, takeouts_dir: Path = None ) -> Iterable[Activity]:
		path = takeouts_dir if takeouts_dir else Path( self._takeouts_dir )
		log.debug( f"Fetching Waze activities from {path}" )

		log.debug( f"Using {field_size_limit()} as field size limit for CSV parser in Waze service" )

		fetched = []
		for file in sorted( path.rglob( ACTIVITY_FILE ) ):
			log.info( f'Fetching activities from Waze takeout in {file}' )
			
			rel_path = file.relative_to( path )
			fetched_takeouts = state[KEY_PLUGINS][self.name]['fetch']['takeouts'].get() or []

			if str( rel_path.as_posix() ) not in fetched_takeouts:
				activities = read_takeout( file )
				for a in activities:
					waze_id = int( a[0][0].strftime( '%Y%m%d%H%M%S' ) )
					fetched.append( Activity( self._prototype( waze_id, a[0][0], rel_path ), 0, classifier=self.name ) )

				fetched_takeouts.append( str( rel_path.as_posix() ) )
				state[KEY_PLUGINS][self.name]['fetch']['takeouts'] = fetched_takeouts
			else:
				log.debug( f'skipping reading activities from {str( rel_path.as_posix() )}' )

		log.debug( f'Fetched {len( fetched )} Waze activities' )

		return fetched

	def _download_file( self, activity: Activity, resource: Resource ) -> Tuple[Any, int]:
		log.debug( f"Using {field_size_limit()} as field size limit for CSV parser in Waze service" )
		takeouts_dir = Path( self._takeouts_dir )
		takeout_path = Path( takeouts_dir, activity.metadata['source_path'] )
		#takeout = read_takeout( Path( self._takeouts_dir, a.raw['path'] ) )
		takeout = read_takeout( takeout_path )
		ts = datetime.strptime( str( activity.raw_id ), '%Y%m%d%H%M%S' ).replace( tzinfo=UTC )
		content = None
		for t in takeout:
			if ts == t[0][0]:
				content = to_gpx( t )
		return content, 200 # return always 200

	def _prototype( self, id: int, time: datetime, relative_path: Path ) -> Mapping:
		mapping = {
			KEY_CLASSIFER: self.name,
			KEY_METADATA: {
				'source_path': str( relative_path.as_posix() )
			},
			KEY_RESOURCES: [
				{
					'name': None,
					'type': 'gpx',
					'path': f'{id}.gpx',
					'status': 100
				}
			],
			KEY_RAW: {
				'id': id,
				'time': time
			}
		}
		return mapping

	# nothing to do for now ...
	def setup( self ):
		echo( 'Skipping setup for Waze ... nothing to configure at the moment' )

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

# helper functions

def read_takeout( path: Path, field_limit: int = 131072 ) -> []:
	#field_size_limit( cfg[KEY_PLUGINS][SERVICE_NAME]['field_size_limit'].get( int ) )
	field_size_limit( field_limit )

	activities = []

	with path.open( 'r', encoding='utf-8' ) as f:
		reader = csv_reader( f )
		parse_mode = False
		for row in reader:
			if len( row ) == 3 and row[0] == 'Location details (date':
				parse_mode = True
			elif parse_mode and row:
				try:
					activities.append( read_drive( row[0] ) )
				except RuntimeError:
					log.error( 'Error parsing row' )
			elif parse_mode and not row:
				parse_mode = False

		return activities

def read_drive( s: str ) -> List[Tuple[datetime, float, float]]:
	if not s:
		return []

	points = []
	for item in load_json( s ):
		for key, value in item.items():
			for token in value.split( " => " ):
				if m := match( '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\((\d+\.\d+); (\d+\.\d+)\)', token ):
					timestamp, lat, lon = m.groups()
					points.append( (datetime.strptime( timestamp, '%Y-%m-%d %H:%M:%S' ).replace( tzinfo=UTC ), float( lat ), float( lon )) )
				else:
					raise RuntimeError( 'Error parsing Waze drive' )

	return points

def to_gpx( tokens: List ):
	# create GPX object for track
	gpx = GPX()
	track = GPXTrack()
	gpx.tracks.append( track )
	segment = GPXTrackSegment()
	track.segments.append( segment )

	# parse tokens and store information in GPX
	for token in tokens:
		point = GPXTrackPoint( latitude=token[1], longitude=token[2], time=token[0] )
		segment.points.append( point )

	return bytes( gpx.to_xml(), 'UTF-8' )

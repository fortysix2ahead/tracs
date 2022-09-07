
from csv import field_size_limit
from csv import reader as csv_reader
from datetime import datetime
from os.path import getmtime
from re import match
from typing import Any
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from click import echo
from dateutil.tz import UTC
from dateutil.tz import gettz
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrack
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXTrackSegment
from logging import getLogger
from pathlib import Path

from . import document
from . import service
from .plugin import Plugin
from ..activity_types import ActivityTypes
from ..activity import Activity
from ..activity import Resource
from ..config import GlobalConfig as gc
from ..config import KEY_LAST_FETCH
from ..service import Service
from ..utils import as_datetime

log = getLogger( __name__ )

TAKEOUTS_DIRNAME = 'takeouts'
ACTIVITY_FILE = 'account_activity_3.csv'
SERVICE_NAME = 'waze'
DISPLAY_NAME = 'Waze'

@document
class WazeActivity( Activity ):

	def __post_init__( self ):
		super().__post_init__()

		if self.raw and len( self.raw ) > 0:
			self.raw_id = int( self.raw[0][1].strftime( '%y%m%d%H%M%S' ) )
			self.time = self.raw[0][1]
			self.localtime = as_datetime( self.time, tz=gettz() )

		self.type = ActivityTypes.drive
		self.classifier = f'{SERVICE_NAME}'
		self.uid = f'{self.classifier}:{self.raw_id}'

@service
class Waze( Service, Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self._logged_in = True

	@property
	def _takeouts_dir( self ) -> Path:
		return Path( gc.db_dir, self.name, TAKEOUTS_DIRNAME )

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path for an activity.

		:param activity: activity for which the path shall be calculated
		:param resource: resource
		:param ext: file extension
		:return: path for activity
		"""
		_id = str( activity.raw_id ) if activity else resource.raw_id()
		path = Path( self.base_path, _id[0:2], _id[2:4], _id[4:6], _id )
		if resource:
			path = Path( path, resource.path )
		elif ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def login( self ) -> bool:
		return self._logged_in

	def _fetch( self, takeouts_dir: Path = None, force: bool = False, **kwargs ) -> Iterable[Activity]:
		_field_size_limit = self.cfg_value( 'field_size_limit' )
		log.debug( f"Using {_field_size_limit} as field size limit for CSV parser in Waze service" )

		takeouts_dir = takeouts_dir if takeouts_dir else Path( self._takeouts_dir )
		log.debug( f"Fetching Waze activities from {takeouts_dir}" )

		last_fetch = self.state_value( KEY_LAST_FETCH )

		fetched = []

		for file in sorted( takeouts_dir.rglob( ACTIVITY_FILE ) ):
			log.info( f'Fetching activities from Waze takeout in {file}' )

			# rel_path = file.relative_to( takeouts_dir )
			mtime = datetime.fromtimestamp( getmtime( file ), UTC )

			if last_fetch and datetime.fromisoformat( last_fetch ) >= mtime and not force:
				log.info( f"Skipping Waze takeout in {file} as it is older than the last_fetch timestamp, consider --force to ignore timestamps"  )
				continue

			for tokens, raw_data in read_takeout( file, _field_size_limit ):
				if len( tokens ) > 0:
					fetched.append( self._prototype( tokens, raw_data ) )

		log.debug( f'Fetched {len( fetched )} Waze activities' )

		return fetched

	# noinspection PyMethodMayBeStatic
	def _prototype( self, raw: List[Tuple[int, datetime, float, float]], raw_data: str ) -> WazeActivity:
		raw_id = int( raw[0][1].strftime( '%y%m%d%H%M%S' ) )
		uid = f'{self.name}:{raw_id}'
		resources = [
			Resource( type='raw', path=f'{raw_id}.raw.txt', status= 200, uid=uid, raw_data=raw_data ),
			Resource( type='gpx', path=f'{raw_id}.gpx', status= 100, uid=uid )
		]
		return WazeActivity( raw=raw, resources=resources )

	def download_resource( self, resource: Resource ) -> Tuple[Any, int]:
		raw_path = Path( self.path_for( resource=resource ).parent, f'{resource.raw_id()}.raw.txt' )
		with open( raw_path, mode='r', encoding='UTF-8' ) as p:
			content = p.read()
			drive = read_drive( content )
			gpx = to_gpx( drive )
			return gpx, 200 # return always 200

	# nothing to do for now ...
	def setup( self ):
		echo( 'Skipping setup for Waze ... nothing to configure at the moment' )

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

# helper functions

def read_takeout( path: Path, field_limit: int = 131072 ) -> List[Tuple[List[Tuple[int, datetime, float, float]], str]]:
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
					activities.append( (read_drive( row[0] ), row[0] ) )
				except RuntimeError:
					log.error( 'Error parsing row' )
			elif parse_mode and not row:
				parse_mode = False

	return activities

def read_drive( s: str ) -> List[Tuple[int, datetime, float, float]]:
	if not s:
		return []

	points = []
	s = s.strip( '[]' )
	for segment in s.split( '};{' ):
		# segment = '{' + segment if segment[0] != '{' else segment
		# segment = segment + '}' if segment[-1] != '}' else segment
		segment = segment.strip( '{}' )
		key, value = segment.split( sep=':', maxsplit=1 ) # todo: what exactly is meant by the key being a number starting with 0
		key, value = key.strip( '"' ), value.strip( '"' )
		for token in value.split( " => " ):
			# need to match two versions:
			# version 1 (2020): 2020-01-01 12:34:56(50.000000; 10.000000)
			# version 2 (2022): 2022-01-01 12:34:56 GMT(50.000000; 10.000000)
			if m := match( '(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d).*\((\d+\.\d+); (\d+\.\d+)\)', token ):
				timestamp, lat, lon = m.groups()
				points.append( (int( key ), datetime.strptime( timestamp, '%Y-%m-%d %H:%M:%S' ).replace( tzinfo=UTC ), float( lat ), float( lon )) )
			else:
				raise RuntimeError( f'Error parsing Waze drive while processing token {token}' )

	return points

def to_gpx( tokens: List[Tuple[int, datetime, float, float]] ):
	# create GPX object for track
	gpx = GPX()
	track = GPXTrack()
	gpx.tracks.append( track )
	segment = GPXTrackSegment()
	track.segments.append( segment )

	# parse tokens and store information in GPX
	for token in tokens:
		index, time, latitude, longitude = token 	# todo: token[0] is a segment?
		point = GPXTrackPoint( time=time, latitude=latitude, longitude=longitude )
		segment.points.append( point )

	return bytes( gpx.to_xml(), 'UTF-8' )

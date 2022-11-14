
from csv import field_size_limit
from csv import reader as csv_reader
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from re import match
from typing import Any
from typing import cast
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from click import echo
from dateutil.tz import UTC
from dateutil.tz import gettz
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrack
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXTrackSegment
from logging import getLogger
from pathlib import Path

from . import Registry
from . import document
from . import importer
from . import service
from .handlers import CSVHandler
from tracs.plugins.gpx import GPX_TYPE
from ..handlers import ResourceHandler
from .plugin import Plugin
from ..activity_types import ActivityTypes
from ..activity import Activity
from ..resources import Resource
from ..config import ApplicationContext
from ..config import KEY_LAST_FETCH
from ..service import Service
from ..utils import as_datetime

log = getLogger( __name__ )

TAKEOUTS_DIRNAME = 'takeouts'
ACTIVITY_FILE = 'account_activity_3.csv'

SERVICE_NAME = 'waze'
DISPLAY_NAME = 'Waze'

WAZE_TYPE = 'application/text+waze'
WAZE_TAKEOUT_TYPE = 'application/csv+waze'

@document( type=WAZE_TYPE )
class WazeActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		if len( raw ) > 0:
			self.raw_id = cast( WazePoint, self.raw[0] ).time_as_int()
			self.time = cast( WazePoint, self.raw[0] ).time
			self.localtime = as_datetime( self.time, tz=gettz() )

		self.type = ActivityTypes.drive
		self.classifier = f'{SERVICE_NAME}'
		self.uid = f'{self.classifier}:{self.raw_id}'

@dataclass
class WazePoint:

	str_format = '%y%m%d%H%M%S'

	key: int = field( default = None )
	time: datetime = field( default = None  )
	lat: float = field( default = None  )
	lon: float = field( default = None  )

	def time_as_str( self ) -> str:
		return self.time.strftime( WazePoint.str_format )

	def time_as_int( self ) -> int:
		return int( self.time_as_str() )

@importer( type=WAZE_TYPE )
class WazeImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=WAZE_TYPE, activity_cls=WazeActivity )

	def load( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Resource]:
		if from_str := kwargs.get( 'from_string', False ):
			self.resource = Resource( content=from_str.encode( encoding='UTF-8' ) )
			self.load_data( self.resource )
		else:
			super().load( path, url, **kwargs )

		return self.resource

	def load_data( self, resource: Resource, **kwargs ) -> Any:
		resource.raw = self.read_drive( self.as_str( resource.content ) )

	# noinspection PyMethodMayBeStatic
	def read_drive( self, s: str ) -> List[WazePoint]:
		points: List[WazePoint] = []

		s = s.strip( '[]' )
		for segment in s.split( '};{' ):
			segment = segment.strip( '{}' )
			key, value = segment.split( sep=':', maxsplit=1 ) # todo: what exactly is meant by the key being a number starting with 0?
			key, value = key.strip( '"' ), value.strip( '"' )
			for token in value.split( " => " ):
				# need to match two versions:
				# version 1 (2020): 2020-01-01 12:34:56(50.000000; 10.000000)
				# version 2 (2022): 2022-01-01 12:34:56 GMT(50.000000; 10.000000)
				if m := match( '(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d).*\((\d+\.\d+); (\d+\.\d+)\)', token ):
					timestamp, lat, lon = m.groups()
					points.append( WazePoint( int( key ), datetime.strptime( timestamp, '%Y-%m-%d %H:%M:%S' ).replace( tzinfo=UTC ), float( lat ), float( lon ) ) )
				else:
					raise RuntimeError( f'Error parsing Waze drive while processing token {token}' )

		return points

@importer( type=WAZE_TAKEOUT_TYPE )
class WazeTakeoutImporter( CSVHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=WAZE_TAKEOUT_TYPE )
		self.importer = WazeImporter()

	def load_data( self, resource: Resource, **kwargs ) -> None:
		super().load_data( resource, **kwargs )

		parse_mode = False
		for row in resource.raw:
			if len( row ) == 3 and row[0] == 'Location details (date':
				parse_mode = True

			elif parse_mode and row:
				try:
					r = Resource( raw=self.importer.read_drive( row[0] ), text=row[0], type=WAZE_TAKEOUT_TYPE )
					self.resource.resources.append( r )
				except RuntimeError:
					log.error( 'Error parsing row' )

			elif parse_mode and not row:
				parse_mode = False

@service
class Waze( Service, Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self._logged_in = True

		self.takeout_importer: WazeTakeoutImporter = cast( WazeTakeoutImporter, Registry.importer_for( WAZE_TAKEOUT_TYPE ) )
		self.takeout_importer.field_size_limit = self.cfg_value( 'field_size_limit' )
		log.debug( f'using {self.takeout_importer.field_size_limit} as field size limit for CSV parser in Waze service' )

		self.importer: WazeImporter = cast( WazeImporter, Registry.importer_for( WAZE_TYPE ) )

	def path_for_id( self, local_id: int, base_path: Optional[Path] ) -> Path:
		_id = str( local_id )
		path = Path( _id[0:2], _id[2:4], _id[4:6], _id )
		if base_path:
			path = Path( base_path, path )
		return path

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path for an activity.

		:param activity: activity for which the path shall be calculated
		:param resource: resource
		:param ext: file extension
		:return: path for activity
		"""
		_id = str( activity.raw_id ) if activity else str( resource.raw_id )
		path = Path( self.base_path, _id[0:2], _id[2:4], _id[4:6], _id )
		if resource:
			path = Path( path, resource.path )
		elif ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return None

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		return None

	def login( self ) -> bool:
		return self._logged_in

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		ctx = self._ctx or kwargs.get( 'ctx' )
		takeouts_dir = Path( ctx.takeout_dir, self.name )
		log.debug( f"fetching Waze activities from {takeouts_dir}" )

		last_fetch = self.state_value( KEY_LAST_FETCH )
		summaries = []

		for file in sorted( takeouts_dir.rglob( ACTIVITY_FILE ) ):
			log.debug( f'fetching activities from Waze takeout in {file}' )

			rel_path = file.relative_to( takeouts_dir ).parent
			if (_takeouts := self.state_value( 'takeouts' )) and rel_path.name in _takeouts:
				continue

			# don't look at mtime, not convenient during development
			# mtime = datetime.fromtimestamp( getmtime( file ), UTC )
			# if last_fetch and datetime.fromisoformat( last_fetch ) >= mtime and not force:
			#	log.debug( f"skipping Waze takeout in {file} as it is older than the last_fetch timestamp, consider --force to ignore timestamps"  )
			#	continue

			takeout_resource = self.takeout_importer.load( path=file )
			for resource in takeout_resource.resources:
				local_id = cast( WazePoint, resource.raw[0] ).time_as_int()
				resource.path = f'{local_id}.raw.txt'
				resource.status = 200
				# resource.source = file.as_uri() # don't save the source right now
				resource.summary = True
				resource.type = WAZE_TYPE
				resource.uid = f'{self.name}:{local_id}'

				summaries.append( resource )

		log.debug( f'fetched {len( summaries )} Waze activities' )

		return summaries

	def download( self, activity: Optional[Activity] = None, summary: Optional[Resource] = None, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		try:
			local_id, uid = summary.raw_id, summary.uid
			resource = Resource( type=GPX_TYPE, path=f'{local_id}.gpx', status=100, uid=uid )
			self.download_resource( resource, summary = summary )
			return [ resource ]

		except RuntimeError:
			log.error( f'error fetching resources',exc_info=True )
			return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		if (summary := kwargs.get( 'summary' )) and summary.raw:
			resource.raw, resource.content = to_gpx( summary.raw )
			resource.status = 200
		else:
			local_path = Path( self.path_for( resource=resource ).parent, f'{resource.local_id}.raw.txt' )
			with open( local_path, mode='r', encoding='UTF-8' ) as p:
				content = p.read()
				drive = self.importer.read_drive( content )
				gpx = to_gpx( drive )
				return gpx, 200 # return always 200

	# nothing to do for now ...
	def setup( self, ctx: ApplicationContext ):
		echo( 'Skipping setup for Waze ... nothing to configure at the moment' )

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

# helper functions

def to_gpx( points: List[WazePoint] ) -> Tuple[GPX, bytes]:
	trackpoints = [ GPXTrackPoint( time=p.time, latitude=p.lat, longitude=p.lon ) for p in points ]
	segment = GPXTrackSegment( points = trackpoints )
	track = GPXTrack()
	track.segments.append( segment )
	gpx = GPX()
	gpx.tracks.append( track )
	return gpx, bytes( gpx.to_xml(), 'UTF-8' )

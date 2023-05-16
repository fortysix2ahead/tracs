from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from logging import getLogger
from pathlib import Path
from re import compile as regex_compile
from typing import Any, cast, List, Optional, Tuple, Union

from dateutil.parser import parse as parse_datetime
from dateutil.tz import gettz, UTC
from gpxpy.gpx import GPX, GPXTrack, GPXTrackPoint, GPXTrackSegment

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.handlers import ResourceHandler
from tracs.plugins.csv import CSVHandler
from tracs.plugins.gpx import GPX_TYPE, GPXImporter
from tracs.registry import importer, Registry, service
from tracs.resources import Resource
from tracs.service import Service
from tracs.utils import as_datetime

log = getLogger( __name__ )

TAKEOUTS_DIRNAME = 'takeouts'
ACTIVITY_FILE = 'account_activity_3.csv'

SERVICE_NAME = 'waze'
DISPLAY_NAME = 'Waze'

WAZE_TYPE = 'text/vnd.waze+txt'
WAZE_ACCOUNT_ACTIVITY_TYPE = 'text/vnd.waze.activity+csv'
WAZE_ACCOUNT_INFO_TYPE = 'text/vnd.waze.info+csv'
WAZE_TAKEOUT_TYPE = WAZE_ACCOUNT_ACTIVITY_TYPE # for backward compatibility

DEFAULT_FIELD_SIZE_LIMIT = 131072

@dataclass
class Point:

	str_format = '%y%m%d%H%M%S'

	time: datetime = field( default=None )
	lat: float = field( default=None )
	lon: float = field( default=None )

	def __post_init__(self):
		self.lat = float( self.lat ) if type( self.lat ) is str else self.lat
		self.lon = float( self.lon ) if type( self.lon ) is str else self.lon
		if type( self.time ) is str:
			self.time = parse_datetime( self.time )
			# self.time = datetime.strptime( self.time, '%Y-%m-%d %H:%M:%S' ).replace( tzinfo=UTC ) if type( self.time ) is str else self.time

	def time_as_str( self ) -> str:
		return self.time.strftime( Point.str_format )

	def time_as_int( self ) -> int:
		return int( self.time_as_str() )

@dataclass
class WazeActivity:

	points: List[Point] = field( default_factory=list )

@dataclass
class DriveSummary:

	date: str = field( default=None )
	destination: str = field( default=None )
	source: str = field( default=None )

@dataclass
class Favourite:

	place: str = field( default=None )
	name: str = field( default=None )
	type: str = field( default=None )

@dataclass
class LocationDetail:

	DATE = regex_compile( r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (GMT|UTC)$' )
	COORDS_1 = regex_compile( r'^\(\d+\.\d+ \d+\.\d+\)$' )
	COORDS_2 = regex_compile( r'^\d{4}-\d{2}-\d{2} \d{2}\:\d{2}\:\d{2} UTC\(\d+\.\d+ \d+\.\d+\)$' )
	COORDS_LIST_1 = regex_compile( r'^\([\d\. ]+\)(\|\([\d\. ]+\))*$' )
	COORDS_LIST_2 = regex_compile( r'^[\d-]+ [\d\:]+ UTC\([\d\. ]+\)(\|[\d-]+ [\d\:]+ UTC\([\d\. ]+\))*' )

	CURLY_BRACES = regex_compile( r'\{.+?\}' )

	# date format can be:
	# - 2023-02-19 13:40:19 GMT
	# - 2023-02-19 13:40:19 UTC
	date: str = field( default=None )

	# coordinate formats:
	# - 2020: [{"0":"2020-07-03 09:30:26(50.0; 10.0) => 2020-07-03 09:30:32(50.1; 10.1) ...
	# - 2022: [{"0":"2020-07-03 09:30:26 GMT(50.0; 10.0) => 2020-07-03 09:30:32 GMT(50.1; 10.1) ...
	# - 2023 V1: (10.0 50.0)|(10.1 50.1)| ...
	# - 2023 V2: 2023-02-23 13:49:52 UTC(50.0 10.0)|2023-02-23 13:49:55 UTC(50.1 10.1)| ...
	coordinates: str = field( default=None )

	def __post_init__(self):
		self.coordinates = self.coordinates.strip()

	def as_point_list( self ) -> List[Point]:
		if self.coordinates[0] == '[' and self.coordinates[-1] == ']':
			segments = self.__class__.CURLY_BRACES.findall( self.coordinates )
			segments = [s[6:-2] for s in segments]
			all_points = []
			for s in segments:
				points = s.split( ' => ' )
				points = [p[:-1].split( '(' ) for p in points]
				points = [[p[0], *p[1].split( '; ' ) ] for p in points]
				all_points.extend( [Point( time=p[0], lat=p[1], lon=p[2] ) for p in points] )
			points = all_points
		else:
			points = self.coordinates.split( '|' )
			if points and self.__class__.COORDS_1.match( points[0] ):
				points = [p[1:-1].split( ' ' ) for p in points]  # format: lon lat!!
				points = [Point( lon=float( p[0] ), lat=float( p[1] ) ) for p in points]
			elif points and self.__class__.COORDS_2.match( points[0] ):
				points = [p[:-1].split( '(' ) for p in points ]
				points = [[p[0], *p[1].split( ' ' ) ] for p in points] # format lat lon!!
				points = [ Point( time=p[0], lat=p[1], lon=p[2] ) for p in points ]
			else:
				raise RuntimeError( f'unsupported format error, example: {points[0]}' )

		return points

	def id( self ):
		return self.as_point_list()[0].time_as_str()

	# this is just for testing
	def validate( self ) -> bool:
		b1 = bool( self.__class__.DATE.match( self.date ) )
		b2 = bool( self.__class__.COORDS_LIST_1.match( self.coordinates ) )
		b3 = bool( self.__class__.COORDS_LIST_2.match( self.coordinates ) )
		b = b1 and ( b2 or b3 )
		return b

@dataclass
class LoginDetail:

	login_time: str = field( default=None )
	logout_time: str = field( default=None )
	total_distance_kilometers: str = field( default=None )
	device_manufacturer: str = field( default=None )
	device_model: str = field( default=None )
	unknown: str = field( default=None )
	device_os_version: str = field( default=None )
	waze_version: str = field( default=None )

@dataclass
class UsageData:

	driven_kilometers: str = field( default=None )
	reports: str = field( default=None )
	map_edits: str = field( default=None )
	munched_meters: str = field( default=None )

@dataclass
class EditHistoryEntry:

	time: str = field( default=None )
	operation: str = field( default=None )
	unknown_field_1: str = field( default=None )
	unknown_field_2: str = field( default=None )

@dataclass
class Photo:

	name: str = field( default=None )
	image: str = field( default=None )

@dataclass
class SearchHistoryEntry:

	time: str = field( default=None )
	unknown_field_1: str = field( default=None )
	unknown_field_2: str = field( default=None )
	unknown_field_3: str = field( default=None )
	term: str = field( default=None )
	term_2: str = field( default=None )

@dataclass
class CarpoolPreferences:

	free_text: str = field( default=None )
	max_seats_available: str = field( default=None )
	spoken_languages: str = field( default=None )
	quiet_ride: str = field( default=None )
	pets_allowed: str = field( default=None )
	smoking_allowed: str = field( default=None )

@dataclass
class UserReport:

	event_date: str = field( default=None )
	type: str = field( default=None )
	pos_x: str = field( default=None )
	pos_y: str = field( default=None )
	subtype: str = field( default=None )

@dataclass
class UserFeedback:

	event_date: str = field( default=None )
	type: str = field( default=None )
	alert_type: str = field( default=None )

@dataclass
class UserCounters:

	traffic_feedback: str = field( default=None )
	gas_prices: str = field( default=None )
	report: str = field( default=None )
	points: str = field( default=None )
	drive: str = field( default=None )

@dataclass
class AccountActivity:

	drive_summaries: List[DriveSummary] = field( default_factory=list )
	favourites: List[Favourite] = field( default_factory=list )
	location_details: List[LocationDetail] = field( default_factory=list )
	login_details: List[LoginDetail] = field( default_factory=list )
	usage_data: UsageData = field( default=UsageData() )
	edit_history: List[EditHistoryEntry] = field( default_factory=list )
	photos_added: List[Photo] = field( default_factory=list )
	search_history: List[SearchHistoryEntry] = field( default_factory=list )
	user_reports: List[UserReport] = field( default_factory=list )
	user_feedback: List[UserFeedback] = field( default_factory=list )
	carpool_preferences: CarpoolPreferences = field( default=CarpoolPreferences() )

@dataclass
class AccountInfo:

	email: str = field( default=None )
	entry_date: str = field( default=None )
	user_name: str = field( default=None )
	first_name: str = field( default=None )
	last_name: str = field( default=None )
	last_login: str = field( default=None )
	connected_accounts: List[str] = field( default_factory=list )
	user_reports: List[UserReport] = field( default_factory=list )
	user_feedback: List[UserFeedback] = field( default_factory=list )
	user_counters: UserCounters = field( default=UserCounters() )

@dataclass
class Takeout:

	account_activity: AccountActivity = field( default=AccountActivity() )
	account_info: AccountInfo = field( default=AccountInfo() )

@importer( type=WAZE_ACCOUNT_ACTIVITY_TYPE )
class WazeAccountActivityImporter( CSVHandler ):

	class Mode( Enum ):
		NONE = 'NONE'
		DRIVE_SUMMARY = '\ufeffdrive summary'
		FAVOURITES = 'favorites'
		LOCATION_DETAILS = 'location details'
		LOCATION_DETAILS_2 = 'location details (date, time, coordinates)'
		LOGIN_DETAILS = 'login details'
		USAGE_DATA_SNAPSHOT = 'snapshot of your waze usage'
		EDIT_HISTORY = 'edit history'
		PHOTOS_ADDED = 'photos added to the map'
		USER_REPORTS = 'user reports'
		USER_FEEDBACK = 'user feedback'
		SEARCH_HISTORY = 'search history'
		CARPOOL_PREFERENCES = 'carpool preferences'

		@classmethod
		def mode_by_value( cls, line: Union[str, List[str]] ):
			# print( f'mode by value for: {line}' )

			# special treatment ...
			if line == [ 'Location details (date', ' time', ' coordinates)' ]:
				line = [ 'Location details (date, time, coordinates)' ]

			if len( line ) != 1:
				return cls.NONE

			return next( iter( [m for m in cls if m.value == line[0].lower()] ), cls.NONE )

	def __init__( self ) -> None:
		super().__init__( resource_type=WAZE_ACCOUNT_ACTIVITY_TYPE, activity_cls=AccountActivity )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		account_activity = AccountActivity()
		while raw:
			line = raw.pop( 0 )
			mode = WazeAccountActivityImporter.Mode.mode_by_value( line )

			if mode == WazeAccountActivityImporter.Mode.DRIVE_SUMMARY:
				while line:
					if (line := raw.pop( 0 )) and line != ['Date', 'Destination', 'Source']:
						account_activity.drive_summaries.append( DriveSummary( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.FAVOURITES:
				while line:
					if (line := raw.pop( 0 )) and line != ['Place', 'Name', 'Type']:
						account_activity.favourites.append( Favourite( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.LOCATION_DETAILS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Date', 'Coordinates']:
						account_activity.location_details.append( LocationDetail( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.LOCATION_DETAILS_2:
				while line:
					if line := raw.pop( 0 ):
						account_activity.location_details.append( LocationDetail( coordinates=line[0] ) )

			elif mode == WazeAccountActivityImporter.Mode.LOGIN_DETAILS:
				while line:
					if (line := raw.pop( 0 )) and line[0] != 'Login Time' and line[1] != 'Logout Time':
						account_activity.login_details.append( LoginDetail( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USAGE_DATA_SNAPSHOT:
				header = raw.pop( 0 )
				data = raw.pop( 0 )
				for h, d in zip( header, data ):
					setattr( account_activity.usage_data, _snake( h ), d )

			elif mode == WazeAccountActivityImporter.Mode.EDIT_HISTORY:
				while line:
					if line := raw.pop( 0 ):
						account_activity.edit_history.append( EditHistoryEntry( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USER_REPORTS:
				while line:
					if line := raw.pop( 0 ):
						account_activity.user_reports.append( UserReport( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USER_FEEDBACK:
				while line:
					if line := raw.pop( 0 ):
						account_activity.user_feedback.append( UserFeedback( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.PHOTOS_ADDED:
				while line:
					if (line := raw.pop( 0 )) and line != ['Name', 'Image']:
						account_activity.photos_added.append( Photo( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.SEARCH_HISTORY:
				while line:
					if line := raw.pop( 0 ):
						account_activity.search_history.append( SearchHistoryEntry( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.CARPOOL_PREFERENCES:
				header = raw.pop( 0 )
				data = raw.pop( 0 )
				for h, d in zip( header, data ):
					setattr( account_activity.carpool_preferences, _snake( h ), d )

			else:
				if line:
					log.error( f'unsupported CSV section detected: "{line}"' )

		return account_activity

@importer( type=WAZE_ACCOUNT_INFO_TYPE )
class WazeAccountInfoImporter( CSVHandler ):

	class Mode( Enum ):
		NONE = 'NONE'
		GENERAL_INFO = '\ufeffgeneral info'
		CONNECTED_ACCOUNTS = 'connected accounts'
		USER_REPORTS = 'user reports'
		USER_FEEDBACK = 'user feedback'
		USER_COUNTERS = 'user counters'

		@classmethod
		def mode_by_value( cls, line: str ):
			if len( line ) != 1:
				return cls.NONE
			return next( iter( [m for m in cls if m.value == line[0].lower()] ), cls.NONE )

	def __init__( self ) -> None:
		super().__init__( resource_type=WAZE_ACCOUNT_INFO_TYPE, activity_cls=AccountInfo )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		account_info = AccountInfo()
		while raw:
			line = raw.pop( 0 )
			mode = WazeAccountInfoImporter.Mode.mode_by_value( line )

			if mode == WazeAccountInfoImporter.Mode.GENERAL_INFO:
				while line:
					if line := raw.pop( 0 ):
						setattr( account_info, _snake( line[0] ), line[1] )

			elif mode == WazeAccountInfoImporter.Mode.CONNECTED_ACCOUNTS:
				while line:
					if line := raw.pop( 0 ):
						account_info.connected_accounts.append( line[0] )

			elif mode == WazeAccountInfoImporter.Mode.USER_REPORTS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Event Date', 'Type', 'Pos X', 'Pos Y', 'Subtype']:
						account_info.user_reports.append( UserReport( *line ) )

			elif mode == WazeAccountInfoImporter.Mode.USER_FEEDBACK:
				while line:
					if (line := raw.pop( 0 )) and line != ['Event Date','Type','Alert Type']:
						account_info.user_feedback.append( UserFeedback( *line ) )

			elif mode == WazeAccountInfoImporter.Mode.USER_COUNTERS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Count','Name']:
						setattr( account_info.user_counters, line[1], line[0] )

		return account_info

@importer( type=WAZE_TYPE, activity_cls=WazeActivity, summary=True )
class WazeImporter( ResourceHandler ):

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return LocationDetail( coordinates=content.decode( 'UTF-8' ) )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		return WazeActivity( raw.as_point_list() )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		wa: WazeActivity = resource.data
		return Activity(
			time=as_datetime( wa.points[0].time, tz=UTC ),
			localtime=as_datetime( wa.points[0].time, tz=gettz() ),
			type=ActivityTypes.drive,
			uids=[f'{SERVICE_NAME}:{wa.points[0].time_as_int()}']
		)

@service
class Waze( Service ):

	def __init__( self, **kwargs ):
		super().__init__( **{ **{'name': SERVICE_NAME, 'display_name': DISPLAY_NAME}, **kwargs } )

		self._takeout_importer: WazeAccountActivityImporter = Registry.importer_for( WAZE_ACCOUNT_ACTIVITY_TYPE )
		self._info_importer: WazeAccountInfoImporter = Registry.importer_for( WAZE_ACCOUNT_INFO_TYPE ) # don't need this at the moment
		self._drive_importer: WazeImporter = cast( WazeImporter, Registry.importer_for( WAZE_TYPE ) )
		self._gpx_importer: GPXImporter = cast( GPXImporter, Registry.importer_for( GPX_TYPE ) )

		self._takeout_importer.field_size_limit = kwargs.get( 'field_size_limit' ) or DEFAULT_FIELD_SIZE_LIMIT

		self._logged_in = True

	@property
	def field_size_limit( self ) -> int:
		return self._takeout_importer.field_size_limit

	@field_size_limit.setter
	def field_size_limit( self, field_size_limit: int ) -> None:
		if hasattr( self, '_takeout_importer' ):
			self._takeout_importer.field_size_limit = field_size_limit

	def path_for_id( self, local_id: Union[int, str], base_path: Optional[Path] = None, resource_path: Optional[Path] = None ) -> Path:
		path = Path( str( local_id )[0:2], str( local_id )[2:4], str( local_id )[4:6], str( local_id ) )
		path = Path( base_path, path ) if base_path else path
		path = Path( path, resource_path ) if resource_path else path
		return path

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return None

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		return None

	def login( self ) -> bool:
		return self._logged_in

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		if not kwargs.get( 'from_takeouts', False ):
			return []

		takeouts_dir = self.ctx.takeouts_dir_for( self.name )
		log.debug( f"fetching Waze activities from {takeouts_dir}" )

		takeout_files = sorted( takeouts_dir.rglob( ACTIVITY_FILE ) )

		self.ctx.total( len( takeout_files ) )
		# last_fetch = self.state_value( KEY_LAST_FETCH )

		summaries = []

		for file in takeout_files:
			self.ctx.advance( f'{file}' )
			log.debug( f'fetching activities from Waze takeout in {file}' )

			takeout_resource = self._takeout_importer.load( path=file )
			account_activity = cast( AccountActivity, takeout_resource.data )
			for ld in account_activity.location_details:
				# ignore drives without timestamps, see issue #74
				if not all( p.time for p in ld.as_point_list() ):
					continue

				summaries.append( Resource(
					content=ld.coordinates.encode( 'UTF-8' ),
					path=f'{ld.id()}.txt',
					raw=ld, # this allows to skip parsing again
					source=str( file.relative_to( takeouts_dir ) ),
					summary=True,
					type=WAZE_TYPE,
					uid=f'{self.name}:{ld.id()}'
				) )

		# self.ctx.complete( 'done' )

		log.debug( f'fetched {len( summaries )} Waze activities' )

		return summaries

	def download( self, summary: Resource, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		if not summary.get_child( GPX_TYPE ) or force: # todo: not sure if this can be false any longer?
			try:
				gpx_resource = Resource( type=GPX_TYPE, path=f'{summary.local_id}.gpx', uid=summary.uid )
				self.download_resource( gpx_resource, summary=summary )
				return [gpx_resource]
			except RuntimeError:
				log.error( f'error fetching resource from {summary.uid}', exc_info=True )
		return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		if (summary := kwargs.get( 'summary' )) and summary.raw:
			resource.raw, resource.content = to_gpx( cast( LocationDetail, summary.raw ).as_point_list() )
			resource.status = 200
		else:
			local_path = Path( self.path_for( resource=resource ).parent, f'{resource.local_id}.txt' )
			with open( local_path, mode='r', encoding='UTF-8' ) as p:
				content = p.read()
				drive = self._drive_importer.read_drive( content )
				gpx = to_gpx( drive )
				return gpx, 200  # return always 200

	# def postdownload( self, ctx: ApplicationContext ) -> None:
	# 	summary = import_session.last_summary
	# 	if activity := import_session.fetched_activities.get( (summary.uid, summary.path) ):
	# 		gpx_activity = self.gpx_importer.as_activity( import_session.last_download[0] )
	# 		new_activity = Activity().init_from( activity ).init_from( other=gpx_activity )
	# 		new_activity.uids.append( activity.uid )
	# 		ctx.db.upsert_activity( new_activity, uid=activity.uid )

# helper functions

def to_gpx( points: List[Point] ) -> Tuple[GPX, bytes]:
	trackpoints = [GPXTrackPoint( time=p.time, latitude=p.lat, longitude=p.lon ) for p in points]
	segment = GPXTrackSegment( points=trackpoints )
	track = GPXTrack()
	track.segments.append( segment )
	gpx = GPX()
	gpx.tracks.append( track )
	return gpx, bytes( gpx.to_xml(), 'UTF-8' )

# helper

def _snake( s: str ) -> str:
	return s.lower().replace( ' ', '_' )

from datetime import datetime
from re import compile
from typing import List

from attrs import define, field
from dateutil.parser import parse as parse_datetime

@define
class Point:

	str_format = '%y%m%d%H%M%S'

	time: datetime = field( default=None )
	lat: float = field( default=None )
	lon: float = field( default=None )

	def __attrs_post_init__(self):
		self.lat = float( self.lat ) if type( self.lat ) is str else self.lat
		self.lon = float( self.lon ) if type( self.lon ) is str else self.lon
		if type( self.time ) is str:
			self.time = parse_datetime( self.time )
			# self.time = datetime.strptime( self.time, '%Y-%m-%d %H:%M:%S' ).replace( tzinfo=UTC ) if type( self.time ) is str else self.time

	def time_as_str( self ) -> str:
		return self.time.strftime( Point.str_format )

	def time_as_int( self ) -> int:
		return int( self.time_as_str() )

@define
class WazeActivity:

	points: List[Point] = field( factory=list )

@define
class DriveSummary:

	date: str = field( default=None )
	destination: str = field( default=None )
	source: str = field( default=None )

@define
class Favourite:

	place: str = field( default=None )
	name: str = field( default=None )
	type: str = field( default=None )

@define
class LocationDetail:

	# date format can be:
	# - 2023-02-19 13:40:19 GMT
	# - 2023-02-19 13:40:19 UTC
	date: str = field( default=None )

	# coordinate formats:
	# - 2020: [{"0":"2020-07-03 09:30:26(50.0; 10.0) => 2020-07-03 09:30:32(50.1; 10.1) ...
	# - 2022: [{"0":"2020-07-03 09:30:26 GMT(50.0; 10.0) => 2020-07-03 09:30:32 GMT(50.1; 10.1) ...
	# - 2023 V1: (10.0 50.0)|(10.1 50.1)| ...
	# - 2023 V2: 2023-02-23 13:49:52 UTC(50.0 10.0)|2023-02-23 13:49:55 UTC(50.1 10.1)| ...
	# - 2024: 2024-09-02 14:21:45+00(10.0 50.0)|2024-09-02 14:21:49+00(10.1 50.1)| ...
	# unclear how this was created:
	# - 1970-01-01 00:35:40 UTC,1970-01-01 00:35:40+00(14.0 50.0)|1970-01-01 00:35:46+00(14.1 50.1)

	coordinates: str = field( default=None )

	def __attrs_post_init__( self ):
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
			elif points and self.__class__.COORDS_3.match( points[0] ):
				points = [p[:-1].split( '(' ) for p in points]
				points = [[p[0], *p[1].split( ' ' )] for p in points]  # format lon lat!!
				points = [Point( time=p[0], lat=p[2], lon=p[1] ) for p in points]
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

@define
class LoginDetail:

	login_time: str = field( default=None )
	logout_time: str = field( default=None )
	total_distance_kilometers: str = field( default=None )
	device_manufacturer: str = field( default=None )
	device_model: str = field( default=None )
	unknown: str = field( default=None )
	device_os_version: str = field( default=None )
	waze_version: str = field( default=None )

@define
class UsageData:

	driven_kilometers: str = field( default=None )
	reports: str = field( default=None )
	map_edits: str = field( default=None )
	munched_meters: str = field( default=None )

@define
class EditHistoryEntry:

	time: str = field( default=None )
	operation: str = field( default=None )
	unknown_field_1: str = field( default=None )
	unknown_field_2: str = field( default=None )

@define
class Photo:

	name: str = field( default=None )
	image: str = field( default=None )

@define
class SearchHistoryEntry:

	time: str = field( default=None )
	unknown_field_1: str = field( default=None )
	unknown_field_2: str = field( default=None )
	unknown_field_3: str = field( default=None )
	term: str = field( default=None )
	term_2: str = field( default=None )

@define
class CarpoolPreferences:

	free_text: str = field( default=None )
	max_seats_available: str = field( default=None )
	spoken_languages: str = field( default=None )
	quiet_ride: str = field( default=None )
	pets_allowed: str = field( default=None )
	smoking_allowed: str = field( default=None )

@define
class UserReport:

	event_date: str = field( default=None )
	type: str = field( default=None )
	pos_x: str = field( default=None )
	pos_y: str = field( default=None )
	subtype: str = field( default=None )

@define
class UserFeedback:

	event_date: str = field( default=None )
	type: str = field( default=None )
	alert_type: str = field( default=None )

@define
class UserCounters:

	traffic_feedback: str = field( default=None )
	gas_prices: str = field( default=None )
	report: str = field( default=None )
	points: str = field( default=None )
	drive: str = field( default=None )

@define
class AccountActivity:

	drive_summaries: List[DriveSummary] = field( factory=list )
	favourites: List[Favourite] = field( factory=list )
	location_details: List[LocationDetail] = field( factory=list )
	login_details: List[LoginDetail] = field( factory=list )
	usage_data: UsageData = field( default=UsageData() )
	edit_history: List[EditHistoryEntry] = field( factory=list )
	photos_added: List[Photo] = field( factory=list )
	search_history: List[SearchHistoryEntry] = field( factory=list )
	user_reports: List[UserReport] = field( factory=list )
	user_feedback: List[UserFeedback] = field( factory=list )
	carpool_preferences: CarpoolPreferences = field( default=CarpoolPreferences() )

@define
class AccountInfo:

	email: str = field( default=None )
	entry_date: str = field( default=None )
	user_name: str = field( default=None )
	first_name: str = field( default=None )
	last_name: str = field( default=None )
	last_login: str = field( default=None )
	connected_accounts: List[str] = field( factory=list )
	user_reports: List[UserReport] = field( factory=list )
	user_feedback: List[UserFeedback] = field( factory=list )
	user_counters: UserCounters = field( default=UserCounters() )

@define
class Takeout:

	account_activity: AccountActivity = field( default=AccountActivity() )
	account_info: AccountInfo = field( default=AccountInfo() )

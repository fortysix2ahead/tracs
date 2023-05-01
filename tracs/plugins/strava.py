from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging import getLogger
from pathlib import Path
from re import compile, findall, match
from sys import exit as sysexit
from time import time
from typing import Any, cast, Dict, List, Optional, Tuple, Union
from webbrowser import open as open_url

from dateutil.tz import gettz, tzlocal, UTC
from rich.prompt import Prompt
from stravalib.client import Client

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.config import ApplicationContext, APPNAME, console
from tracs.plugins.fit import FIT_TYPE
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import JSON_TYPE, JSONHandler
from tracs.plugins.tcx import TCX_TYPE
from tracs.registry import importer, Registry, service, setup
from tracs.resources import Resource
from tracs.service import Service
from tracs.utils import seconds_to_time as stt, to_isotime

log = getLogger( __name__ )

SERVICE_NAME = 'strava'
DISPLAY_NAME = 'Strava'

STRAVA_TYPE = 'application/vnd.strava+json'

BASE_URL = 'https://www.strava.com'
AUTH_URL = f'{BASE_URL}/oauth/authorize'
TOKEN_URL = f'{BASE_URL}/oauth/token'
OAUTH_REDIRECT_URL = 'http://localhost:40004'
SCOPE = 'activity:read_all'

FETCH_PAGE_SIZE = 30 #

TIMEZONE_FULL_REGEX = compile( '^(\(.+\)) (.+)$' ) # not used at the moment
TIMEZONE_REGEX = compile( '\(\w+\+\d\d:\d\d\) ' )

HEADERS_TEMPLATE = {
}

HEADERS_LOGIN = { **HEADERS_TEMPLATE, **{
	'Accept': '*/*',
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'en-US,en;q=0.5',
	'Cache-Control': 'no-cache',
	'Connection': 'keep-alive',
	'Content-Type': 'application/x-www-form-urlencoded',
	'DNT': '1',
	'Host': 'www.strava.com',
	'Origin': 'https://www.strava.com',
	'Pragma': 'no-cache',
	'Referer': 'https://www.strava.com/login',
	'TE': 'Trailers',
	'Upgrade-Insecure-Requests': '1',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
} }

TYPES = {
	'AlpineSki': ActivityTypes.ski,
	'BackcountrySki': ActivityTypes.xcski_backcountry,
	'Canoeing': ActivityTypes.canoe,
	'Crossfit': ActivityTypes.crossfit,
	'EBikeRide': ActivityTypes.bike_ebike,
	'Elliptical': ActivityTypes.other,
	'Golf': ActivityTypes.golf,
	'Handcycle': ActivityTypes.bike_hand,
	'Hike': ActivityTypes.hiking,
	'IceSkate': ActivityTypes.ice_skate,
	'InlineSkate': ActivityTypes.inline_skate,
	'Kayaking': ActivityTypes.kayak,
	'Kitesurf': ActivityTypes.kitesurf,
	'NordicSki': ActivityTypes.xcski,
	'Ride': ActivityTypes.bike,
	'RockClimbing': ActivityTypes.climb,
	'RollerSki': ActivityTypes.rollski,
	'Rowing': ActivityTypes.row,
	'Run': ActivityTypes.run,
	'Sail': ActivityTypes.sail,
	'Skateboard': ActivityTypes.skateboard,
	'Snowboard': ActivityTypes.snowboard,
	'Snowshoe': ActivityTypes.snowshoe,
	'Soccer': ActivityTypes.soccer,
	'StairStepper': ActivityTypes.other,
	'StandUpPaddling': ActivityTypes.paddle_standup,
	'Surfing': ActivityTypes.surf,
	'Swim': ActivityTypes.swim,
	'Velomobile': ActivityTypes.other,
	'VirtualRide': ActivityTypes.bike_ergo,
	'VirtualRun': ActivityTypes.run_ergo,
	'Walk': ActivityTypes.walk,
	'WeightTraining': ActivityTypes.gym,
	'Wheelchair': ActivityTypes.other,
	'Windsurf': ActivityTypes.surf_wind,
	'Workout': ActivityTypes.gym,
	'Yoga': ActivityTypes.yoga,
}

@dataclass
class StravaActivity:

	achievement_count: int = field( default=None )
	athlete: Dict[str, int] = field( default_factory=dict )
	athlete_count: int = field( default=None )
	average_cadence: float = field( default=None )
	average_heartrate: float = field( default=None )
	average_speed: float = field( default=None )
	comment_count: int = field( default=None )
	commute: bool = field( default=None )
	display_hide_heartrate_option: bool = field( default=None )
	distance: float = field( default=None )
	elapsed_time: int = field( default=None )
	elev_high: float = field( default=None )
	elev_low: float = field( default=None )
	end_latlng: List[float] = field( default_factory=list )
	external_id: str = field( default=None )
	flagged: bool = field( default=None )
	from_accepted_tag: bool = field( default=None )
	gear_id: Optional[str] = field( default=None )
	has_heartrate: bool = field( default=None )
	has_kudoed: bool = field( default=None )
	heartrate_opt_out: bool = field( default=None )
	id: int = field( default=None )
	kudos_count: int = field( default=None )
	location_city: Optional[str] = field( default=None )
	location_country: Optional[str] = field( default=None )
	location_state: Optional[str] = field( default=None )
	manual: bool = field( default=None )
	map: Dict = field( default_factory=dict )
	max_heartrate: float = field( default=None )
	max_speed: float = field( default=None )
	moving_time: int = field( default=None )
	name: str = field( default=None )
	photo_count: int = field( default=None )
	pr_count: int = field( default=None )
	private: bool = field( default=None )
	resource_state: int = field( default=None )
	sport_type: str = field( default=None )
	start_date: str = field( default=None )
	start_date_local: str = field( default=None )
	start_latlng: List[float] = field( default_factory=list )
	timezone: str = field( default=None )
	total_elevation_gain: float = field( default=None )
	total_photo_count: int = field( default=None )
	trainer: bool = field( default=None )
	type: str = field( default=None )
	upload_id: int = field( default=None )
	upload_id_str: str = field( default=None )
	utc_offset: float = field( default=None )
	visibility: str = field( default=None )
	workout_type: Optional[int] = field( default=None )

	@property
	def local_id( self ) -> int:
		return self.id

@importer( type=STRAVA_TYPE, activity_cls=StravaActivity, summary=True )
class StravaImporter( JSONHandler ):

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: StravaActivity = resource.data
		tz_str = TIMEZONE_REGEX.sub( '', activity.timezone )
		if not (tz := gettz( tz_str ) ):
			tz = tzlocal()

		return Activity(
			name = activity.name,
			type = TYPES.get( activity.type, ActivityTypes.unknown ),
			time = to_isotime( activity.start_date ),
			localtime = to_isotime( activity.start_date ).astimezone( tz ),
			timezone = tz_str,
			distance = activity.distance if activity.distance > 0 else None,
			speed = activity.average_speed if activity.average_speed > 0 else None,
			speed_max = activity.max_speed if activity.max_speed > 0 else None,
			ascent = activity.total_elevation_gain if activity.total_elevation_gain > 0 else None,
			descent = activity.total_elevation_gain if activity.total_elevation_gain > 0 else None,
			elevation_max = activity.elev_high,
			elevation_min = activity.elev_low,
			duration = stt( activity.elapsed_time ) if activity.elapsed_time else None,
			duration_moving = stt( activity.moving_time ) if activity.moving_time else None,
			heartrate = int( activity.average_heartrate ) if activity.average_heartrate else None,
			heartrate_max = int( activity.max_heartrate ) if activity.max_heartrate else None,
			location_country = activity.location_country,
			uids = [f'{SERVICE_NAME}:{activity.id}'],
		)

@service
class Strava( Service ):

	def __init__( self, **kwargs ):
		super().__init__( **{ **{'name': SERVICE_NAME, 'display_name': DISPLAY_NAME, 'base_url': BASE_URL}, **kwargs } )

		self._client = Client()
		self._session = None
		self._oauth_session = None

		self.importer: StravaImporter = cast( StravaImporter, Registry.importer_for( STRAVA_TYPE ) )
		self.json_handler: JSONHandler = cast( JSONHandler, Registry.importer_for( JSON_TYPE ) )

	@property
	def login_url( self ) -> str:
		return f'{self.base_url}/login'

	@property
	def session_url( self ) -> str:
		return f'{self.base_url}/session'

	@property
	def activities_url( self ) -> str:
		return f'{self.base_url}/activities'

	@property
	def auth_url( self ) -> str:
		return f'{self.base_url}/oauth/authorize'

	@property
	def token_url( self ) -> str:
		return f'{self.base_url}/oauth/token'

	@property
	def redirect_url( self ) -> str:
		return OAUTH_REDIRECT_URL

	def url_events_year( self, year, page: int ) -> str:
		after = int( datetime( year, 1, 1, tzinfo=UTC ).timestamp() )
		before = int( datetime( year + 1, 1, 1, tzinfo=UTC ).timestamp() )
		per_page = FETCH_PAGE_SIZE # we might make this configurable later ...
		return f'{self.base_url}/api/v3/athlete/activities?before={before}&after={after}&page={page}&per_page={per_page}'

	def all_events_url( self, page: int ) -> str:
		after = int( datetime( 1970, 1, 1, tzinfo=UTC ).timestamp() )
		before = int( datetime( datetime.utcnow().year + 1, 1, 1, tzinfo=UTC ).timestamp() )
		per_page = FETCH_PAGE_SIZE  # we might make this configurable later ...
		return f'{self.base_url}/api/v3/athlete/activities?before={before}&after={after}&page={page}&per_page={per_page}'

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return f'{self.activities_url}/{local_id}'

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		if type == GPX_TYPE:
			return f'{self._activities_url}/{local_id}/export_gpx'
		elif type == TCX_TYPE:
			return f'{self._activities_url}/{local_id}/export_original'

	def _link_path( self, activity: Activity, ext: str ) -> Path or None:
		#		if activity.id:
		utc = activity.utctime
		parent = Path( self._lib_dir, utc.strftime( '%Y/%m/%d' ) )
		#			a = self.db.get_activity( activity )
		#			if a and a.name:
		#				return Path( parent, f'{utc.strftime( "%H%M%S" )} - {a.name}.strava.{ext}' )  # fully qualified path
		#			else:
		return Path( parent, f'{utc.strftime( "%H%M%S" )}.{self.name}.{ext}' )  # fully qualified path

	def login( self ):
		# check if access/refresh tokens are available
		if not self.state_value( 'access_token' ) and not self.state_value( 'refresh_token' ):
			log.error( f"application setup not complete for {SERVICE_NAME}, consider running {APPNAME} setup --strava" )
			sysexit( -1 )

		self._client = Client( access_token=self.state_value( 'access_token' ) )

		if time() > self.state_value( 'expires_at' ):
			log.debug( f"access token has expired, attempting to fetch new one" )
			client_id = self.cfg_value( 'client_id' )
			client_secret = self.cfg_value( 'client_secret' )
			refresh_token = self.state_value( 'refresh_token' )
			refresh_response = self._client.refresh_access_token( client_id=client_id, client_secret=client_secret, refresh_token=refresh_token )

			self.set_state_value( 'access_token', refresh_response.get( 'access_token' ) )
			self.set_state_value( 'refresh_token', refresh_response.get( 'refresh_token' ) )
			self.set_state_value( 'expires_at', refresh_response.get( 'expires_at' ) )

		# todo: how to detect unsuccessful login?
		return True

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		if not self.login():
			return []

		# self.ctx.start( f'fetching activity summaries from {self.display_name}' )

		resources = []

		activities = self._client.get_activities( after=datetime( 2022, 1, 1 ), before=datetime.utcnow(), limit=FETCH_PAGE_SIZE )

		for a in activities:
			print( a )

		try:
			for page in range( 1, 999999 ):
				self.ctx.advance( f'activities {(page - 1) * FETCH_PAGE_SIZE} to { page * FETCH_PAGE_SIZE } (batch {page})' )

				# status is 429 and raw['message'] = 'Rate Limit Exceeded', when rate goes out of bounds ...
				json_resource = self.json_handler.load( url=self.all_events_url( page ), session=self._oauth_session )

				for item in json_resource.raw:
					resources.append( self.importer.save( item, uid=f"{self.name}:{item['id']}", resource_path=f"{item['id']}.json", resource_type=STRAVA_TYPE, status=200, source=self.url_for_id( item['id'] ), summary=True ) )

				if not json_resource.raw or len( json_resource.raw ) == 0:
					break

		except RuntimeError:
			log.error( f'error fetching activity ids', exc_info=True )

		# finally:
		#	self.ctx.complete( 'done' )

		return resources

	def download( self, summary: Resource, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		try:
			resources = [
				Resource( uid=summary.uid, path=f'{summary.local_id}.gpx', type=GPX_TYPE, source=f'{self.activities_url}/{summary.local_id}/export_gpx' ),
				Resource( uid=summary.uid, source=f'{self.activities_url}/{summary.local_id}/export_original' ) # type is None as this can be tcx or fit
			]

			for r in resources:
				# type handling is more complicated here ...
				if not force:
					if r.type == GPX_TYPE and summary.get_child( r.type ):
						continue

					if r.type is None and ( summary.get_child( TCX_TYPE ) or summary.get_child( FIT_TYPE ) ):
						continue

				try:
					self.download_resource( r )
				except RuntimeError:
					log.error( f'error fetching resource from {r.source}', exc_info=True )

			return [r for r in resources if r.content]

		except RuntimeError:
			log.error( f'error fetching resources', exc_info=True )
			return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		if url := resource.source:
			log.debug( f'downloading resource from {url}' )
			response = self._session.get( url, headers=HEADERS_LOGIN, allow_redirects=True, stream=True )

			content_type = response.headers.get( 'Content-Type' )
			content_disposition = response.headers.get( 'content-disposition' )

			# content type is 'text/html; charset=utf-8' for .gpx resources that do not exist (i.e. for strenth training)
			# disposition is None in such cases
			if content_type.startswith( 'text/html' ) and content_disposition is None:
				resource.status = 404
			else:
				ext = findall( r'^.*filename=\".+\.(\w+)\".*$', content_disposition )[0]
				resource.content = response.content
				resource.type = Registry.resource_type_for_suffix( ext )
				resource.path = f'{resource.local_id}.{ext}'
				resource.status = response.status_code

			# fit is binary, there's no text version to be stored
			if resource.type == FIT_TYPE:
				pass

			# fix for Strava bug where TCX documents contain whitespace before the first XML tag
			# sample first line:
			# '          <?xml version="1.0" encoding="UTF-8"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"> ...'
			if resource.type == TCX_TYPE:
				while resource.content[0:1] == b' ':
					resource.content = resource.content[1:]

			return response.content, response.status_code

		else:
			log.warning( f'unable to determine download url for resource {resource}' )
			return None, 500

	@property
	def logged_in( self ) -> bool:
		return True if self._session and self._oauth_session else False

	def _oauth_token( self ) -> dict:
		return {
			'access_token': self.state_value( 'access_token' ),
			'refresh_token': self.state_value( 'refresh_token' ),
			'token_type': self.state_value( 'token_type' ),
			'expires_at': self.state_value( 'expires_at' ),
			'expires_in': int( self.state_value( 'expires_at' ) - datetime.utcnow().timestamp() )
		}

	def _save_oauth_token( self, token: dict ) -> None:
		self.set_state_value( 'access_token', token['access_token'] )
		self.set_state_value( 'refresh_token', token['refresh_token'] )
		self.set_state_value( 'token_type', token['token_type'] )
		self.set_state_value( 'expires_at', int( token['expires_at'] ) )
		self.set_state_value( 'expires_in', token['expires_in'] )

# setup

INTRO_TEXT = f'GPX and TCX files from Strava will be downloaded via Strava\'s Web API, that\'s why your credentials are needed.'
# https://developers.strava.com/docs/authentication/
CLIENT_ID_TEXT = 'Checking for new activities and downloading photos works by using Strava\'s REST API. To be able ' \
                 'to use this API you need to enter your Client ID and your Client Secret. In order to retrieve both, ' \
                 'you need to create your own Strava application. Head to https://www.strava.com/settings/api ' \
                 'and enter all necessary details. Once you created your application, the ID and the secret ' \
                 'will be displayed.'

# return { 'username': user, 'password': password }, {}

@setup
def setup( ctx: ApplicationContext, config: Dict, state: Dict ) -> Tuple[Dict, Dict]:
	ctx.console.print( INTRO_TEXT, width=120 )

	client = Client()

	ctx.console.print()
	ctx.console.print( CLIENT_ID_TEXT, width=120 )
	ctx.console.print()

	client_id = Prompt.ask( 'Enter your Client ID', console=ctx.console, default=config.get( 'client_id', '' ) )
	ctx.console.print()
	client_secret = Prompt.ask( 'Enter your Client Secret', console=ctx.console, default=config.get( 'client_secret', '' ) )
	ctx.console.print()

	authorize_url = client.authorization_url( client_id=client_id, redirect_uri=OAUTH_REDIRECT_URL, scope=SCOPE )

	client_code_text = f'For the next step we need to obtain the Client Code. The client code can be obtained by visiting this ' \
	                   f'URL: {authorize_url} After authorizing {APPNAME} you will be redirected to {OAUTH_REDIRECT_URL} and the ' \
	                   f'code is part of the URL displayed in your browser. Have a look at the displayed ' \
	                   f'URL: {OAUTH_REDIRECT_URL}?code=<CLIENT_CODE_IS_DISPLAYED_HERE>&scope={SCOPE}'

	ctx.console.print()
	ctx.console.print( client_code_text )
	ctx.console.print()
	client_code = Prompt.ask( f'Enter your Client Code or press enter to open the link in your browser and let {APPNAME} autodetect the code.', console=ctx.console )
	ctx.console.print()

	if not client_code:
		open_url( authorize_url )
		webServer = HTTPServer( ('localhost', 40004), StravaSetupServer )

		try:
			webServer.serve_forever()
		except KeyboardInterrupt:
			pass

		client_code = StravaSetupServer.client_code
		webServer.server_close()

	try:
		token_response = client.exchange_code_for_token( client_id=client_id, client_secret=client_secret, code=client_code )
		access_token = token_response.get( 'access_token' )
		refresh_token = token_response.get( 'refresh_token' )
		expires_at = token_response.get( 'expires_at' )
		log.debug( f"fetched access and refresh token for athlete {client.get_athlete().id}, expiring at {expires_at}" )

		return { 'client_code': client_code, 'client_id': client_id, 'client_secret': client_secret },\
			{ **state, 'access_token': access_token, 'refresh_token': refresh_token, 'expires_at': expires_at }

	except RuntimeError as rte:
		ctx.console.print( f'Error: authorization not granted.' )
		ctx.console.print( rte )
		return {}, {}

class StravaSetupServer( BaseHTTPRequestHandler ):

	client_code = None

	def do_GET(self):
		if m := match( '^.+code=([\da-f]+).*$', self.path ):
			StravaSetupServer.client_code = m[1]
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes("<html><head><title></title></head>", "utf-8"))
		if m[1]:
			self.wfile.write(bytes("<body><p>Client code successfully detected, you can close this window.</p></body>", "utf-8"))
		else:
			self.wfile.write( bytes( "<body><p>Error: unable to detect client code in URL.</p></body>", "utf-8" ) )
		self.wfile.write(bytes("</html>", "utf-8"))
		raise KeyboardInterrupt

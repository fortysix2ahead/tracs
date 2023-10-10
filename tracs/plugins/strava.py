from dataclasses import dataclass
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import zip_longest
from logging import getLogger
from pathlib import Path
from re import compile, match
from sys import exit as sysexit
from time import time
from typing import Any, cast, Dict, List, Optional, Tuple, Union
from webbrowser import open as open_url

from dateutil.parser import parse as dtparse
from dateutil.tz import tzlocal, UTC
from lxml.etree import tostring
from rich.prompt import Prompt
from stravalib.client import Client
from stravalib.model import Activity as StravaActivity

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.config import ApplicationContext, APPNAME
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import JSON_TYPE, JSONHandler
from tracs.plugins.stravaconstants import BASE_URL, TYPES
from tracs.plugins.tcx import TCX_TYPE
from tracs.registry import importer, Registry, service, setup
from tracs.resources import Resource
from tracs.service import Service
from tracs.streams import Point, Stream

log = getLogger( __name__ )

SERVICE_NAME = 'strava'
DISPLAY_NAME = 'Strava'

STRAVA_TYPE = 'application/vnd.strava+json'

OAUTH_REDIRECT_URL = 'http://localhost:40004'
SCOPE = 'activity:read_all'

FETCH_PAGE_SIZE = 30 #

TIMEZONE_FULL_REGEX = compile( '^(\(.+\)) (.+)$' ) # not used at the moment
TIMEZONE_REGEX = compile( '\(\w+\+\d\d:\d\d\) ' )

@importer( type=STRAVA_TYPE, activity_cls=StravaActivity, summary=True )
class StravaHandler( JSONHandler ):

	def load_data( self, raw: Any, **kwargs ):
		return StravaActivity.parse_obj( raw )

	def save_data( self, data: Any, **kwargs ) -> Any:
		return StravaActivity.dict( data )

	# noinspection PyMethodMayBeStatic
	def to_float( self, q ) -> Optional[float]:
		if type( q ) is float:
			return q if q > 0.0 else None
		else:
			return q.magnitude if q and q > 0.0 else None

	# noinspection PyMethodMayBeStatic
	def to_int( self, q ) -> Optional[int]:
		if type( q ) in [int, float]:
			return int( q ) if q > 0 else None
		else:
			return q.magnitude if q and q > 0 else None

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: StravaActivity = resource.data
		tz_str = str( activity.timezone ) if activity.timezone else str( tzlocal() )

		# noinspection Py
		return Activity(
			name = activity.name,
			type = TYPES.get( activity.type, ActivityTypes.unknown ),
			starttime= activity.start_date,
			starttime_local= activity.start_date_local.astimezone( activity.timezone ),
			timezone = tz_str,
			distance = self.to_float( activity.distance ),
			speed = self.to_float( activity.average_speed ),
			speed_max = self.to_float( activity.max_speed ),
			ascent = self.to_float( activity.total_elevation_gain ),
			descent = self.to_float( activity.total_elevation_gain ),
			elevation_max = self.to_float( activity.elev_high ),
			elevation_min = self.to_float( activity.elev_low ),
			duration = activity.elapsed_time,
			duration_moving = activity.moving_time,
			heartrate = self.to_int( activity.average_heartrate ),
			heartrate_max = self.to_int( activity.max_heartrate ),
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

		self.importer: StravaHandler = cast( StravaHandler, Registry.importer_for( STRAVA_TYPE ) )
		self.json_handler: JSONHandler = cast( JSONHandler, Registry.importer_for( JSON_TYPE ) )

	@property
	def activities_url( self ) -> str:
		return f'{self.base_url}/activities'

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
		# self.ctx.start( f'fetching activity summaries from {self.display_name}' )
		resources = []

		after = kwargs.get( 'range_from' )
		before = kwargs.get( 'range_to' )
		first_year = kwargs.get( 'first_year' )

		if after is None or before is None:
			after, before = datetime( first_year, 1, 1 ), datetime.utcnow() + timedelta( days = 1 )

		for a in self._client.get_activities( after=after, before=before ):
			self.ctx.advance( f'activity {a.id}' )

			resources.append( self.importer.save_to_resource(
				content=self.json_handler.save_raw( a.to_dict() ),
				raw = a.to_dict(),
				data = a,
				uid = f'{self.name}:{a.id}',
				path = f'{a.id}.json',
				type=STRAVA_TYPE,
				source=self.url_for_id( a.id ),
				summary = True,
			) )

		#	self.ctx.complete( 'done' )

		return resources

	def download( self, summary: Resource, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		# available streams:
		# time, latlng, distance, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth
		# gpx contains lat/lon, elevation, time + time in metadata
		# tcx contains TotalTimeSeconds, DistanceMeters, MaximumSpeed, Calories
		# track contains Time, LatitudeDegrees, LongitudeDegrees, AltitudeMeters, DistanceMeters, SensorState
		streams = self._client.get_activity_streams( summary.local_id, types=[ 'time', 'latlng', 'distance', 'altitude', 'velocity_smooth', 'heartrate' ] )
		stream = to_stream( streams, summary.data.start_date )

		tcx = stream.as_tcx(
			average_heart_rate_bpm = summary.raw.get( 'average_heartrate' ),
			calories = summary.raw.get( 'calories' ),
			distance_meters = summary.raw.get( 'distance' ),
			id = f'{summary.raw.get( "start_date_local" )}Z',
			intensity = 'Active', # todo: don't know where to get this from
			maximum_heart_rate_bpm = summary.raw.get( 'max_heartrate' ),
			maximum_speed = summary.raw.get( 'max_speed' ),
			start_date = dtparse( sd ) if type( sd := summary.raw.get( 'start_date' ) ) is str else sd,
			# trigger_method = 'Distance', # todo: this is not correct
			total_time_seconds = summary.raw.get( 'elapsed_time' ),
		)
		resources = [
			Resource( uid=summary.uid, path=f'{summary.local_id}.tcx', type=TCX_TYPE, text=tostring( tcx.as_xml(), pretty_print=True ).decode( 'UTF-8' ) )
		]

		if any( p.lat for p in stream.points ):
			gpx = stream.as_gpx(
				track_name = summary.raw.get( 'name' ),
				# track_type = '1' # todo: don't know what GPX type means, strava uses integer numbers
			)
			resources.append(
				Resource( uid=summary.uid, path=f'{summary.local_id}.gpx', type=GPX_TYPE, text=gpx.to_xml( prettyprint=True ) )
			)

		return resources

	@property
	def logged_in( self ) -> bool:
		return True if self._session and self._oauth_session else False

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

# helper

class EmptyStream:

	@property
	def data( self ) -> List:
		return []

EMPTY = EmptyStream()

def to_stream( streams: Dict, start_date: datetime ) -> Stream:
	stream_iterator = zip_longest(
		streams.get( 'time', EMPTY ).data,
		streams.get( 'latlng', EMPTY ).data,
		streams.get( 'distance', EMPTY ).data,
		streams.get( 'altitude', EMPTY ).data,
		streams.get( 'velocity_smooth', EMPTY ).data,
		streams.get( 'heartrate', EMPTY ).data,
		fillvalue=None
	)
	points = [ Point( distance=d, alt=a, speed=vs, hr=hr, start=start_date, seconds=t, latlng=ll ) for t, ll, d, a, vs, hr in stream_iterator ]
	return Stream( points=points )

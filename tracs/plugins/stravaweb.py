from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from re import compile, findall
from sys import exit as sysexit
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from bs4 import BeautifulSoup
from click import echo
from dateutil.tz import UTC
from requests import Session
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
from rich.prompt import Prompt

from tracs.config import ApplicationContext, APPNAME
from tracs.plugins.fit import FIT_TYPE
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import JSONHandler
from tracs.plugins.tcx import TCX_TYPE
from tracs.registry import Registry, service, setup
from tracs.resources import Resource
from tracs.service import Service

log = getLogger( __name__ )

SERVICE_NAME = 'stravaweb'
DISPLAY_NAME = 'Strava Web'

STRAVA_TYPE = 'application/vnd.strava+json'

BASE_URL = 'https://www.strava.com'

FETCH_PAGE_SIZE = 200 # maximum possible size?

TIMEZONE_FULL_REGEX = compile( '^(\(.+\)) (.+)$' ) # not used at the moment
TIMEZONE_REGEX = compile( '\(\w+\+\d\d:\d\d\) ' )

HEADERS_TEMPLATE = {
	'Accept': '*/*',
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'en-US,en;q=0.5',
	'Connection': 'keep-alive',
	'Host': 'www.strava.com',
	'TE': 'Trailers',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
}

HEADERS_LOGIN = { **HEADERS_TEMPLATE, **{
	'Cache-Control': 'no-cache',
	'Content-Type': 'application/x-www-form-urlencoded',
	'DNT': '1',
	'Origin': 'https://www.strava.com',
	'Pragma': 'no-cache',
	'Referer': 'https://www.strava.com/login',
	'Upgrade-Insecure-Requests': '1',
} }

HEADERS_API = { **HEADERS_TEMPLATE,
	'X-CSRF-Token': '', # this needs to be updated later
   'X-Requested-With': 'XMLHttpRequest',
}

@dataclass
class WebActivity:
	activity_type_display_name: str = field( default=None )
	activity_url: str = field( default=None )
	activity_url_for_twitter: str = field( default=None )
	athlete_gear_id: Optional[int] = field( default=None )
	bike_id: Optional[int] = field( default=None )
	commute: Optional[Any] = field( default=None )
	description: Optional[str] = field( default=None )
	display_type: str = field( default=None )
	distance: Optional[float] = field( default=None )
	distance_raw: float = field( default=None )
	elapsed_time: str = field( default=None )
	elapsed_time_raw: int = field( default=None )
	elevation_gain: int = field( default=None )
	elevation_gain_raw: int = field( default=None )
	elevation_unit: str = field( default=None )
	flagged: bool = field( default=None )
	has_latlng: bool = field( default=None )
	hide_heartrate: bool = field( default=None )
	hide_power: bool = field( default=None )
	id: int = field( default=None )
	is_changing_type: bool = field( default=None )
	is_new: bool = field( default=None )
	leaderboard_opt_out: bool = field( default=None )
	long_unit: str = field( default=None )
	moving_time: str = field( default=None )
	moving_time_raw: int = field( default=None )
	name: str = field( default=None )
	private: bool = field( default=None )
	short_unit: str = field( default=None )
	start_date: str = field( default=None )
	start_date_local_raw: int = field( default=None )
	start_day: str = field( default=None )
	start_time: str = field( default=None )
	static_map: Optional[str] = field( default=None )
	suffer_score: Optional[int] = field( default=None )
	trainer: bool = field( default=None )
	twitter_msg: str = field( default=None )
	type: str = field( default=None )
	visibility: str = field( default=None )
	workout_type: Optional[int] = field( default=None )

@dataclass
class ActivityPage:

	models: List[WebActivity] = field( default_factory=list )
	page: int = field( default=None )
	per_page: int = field( default=None )
	total: int = field( default=None )

@service
class Strava( Service ):

	def __init__( self, **kwargs ):
		super().__init__( **{ **{'name': SERVICE_NAME, 'display_name': DISPLAY_NAME, 'base_url': BASE_URL}, **kwargs } )
		self._session: Optional[Session] = None
		self._importer = JSONHandler( 'web', ActivityPage )

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
	def training_url( self ) -> str:
		return f'{self.base_url}/athlete/training'

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

	def login( self ):
		if not self.cfg_value( 'username' ) and not self.cfg_value( 'password' ):
			log.error( f"setup not complete for plugin {DISPLAY_NAME}, consider running {APPNAME} setup {SERVICE_NAME}" )
			sysexit( -1 )

		if not self._session:
			if cookies := self.state_value( 'session' ) and False: # todo: session reuse does not yet work
				session = Session()
				session.cookies.update( cookiejar_from_dict( cookies ) )
				response = session.get( self.training_url )
				if response.status_code == 200:
					self._session = session
				else:
					log.error( f'todo: session expired, status code = {response.status_code}' )
			else:
				self._session = self.login_session()

	# might raise TypeError
	def login_session( self ) -> Session:
		session = Session()
		response = session.get( self.login_url )

		HEADERS_API['X-CSRF-Token'] = BeautifulSoup( response.text, 'html.parser' ).find( 'meta', attrs={ 'name': 'csrf-token' } )['content']
		log.debug( f"successfully detected CSRF token for {SERVICE_NAME} login page: {HEADERS_API['X-CSRF-Token']}" )

		data = {
			'utf8': '✓',
			'authenticity_token': HEADERS_API['X-CSRF-Token'], # token might be None, if BS failed above
			'plan': '',
			'email': self.cfg_value( 'username' ),
			'password': self.cfg_value( 'password' ),
			'remember_me': 'on'
		}
		response = session.post( self.session_url, headers=HEADERS_LOGIN, data=data )

		if response.status_code == 200:
			cookies = dict_from_cookiejar( session.cookies )
			self.set_state_value( 'session', cookies )
			return session
		else:
			log.error( f'web login failed for {DISPLAY_NAME}, are the credentials correct?' )

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		if not self._session:
			self.login()

		url = 'https://www.strava.com/athlete/training_activities'
		parameters = {
			'keywords': '',
		   'activity_type': '',
		   'workout_type': '',
		   'commute': '',
		   'private_activities': '',
		   'trainer': '',
			'gear': '',
			'search_session_id': uuid4(),
			'new_activity_only': 'false'
		}
		# url = 'https://www.strava.com/athlete/training_activities?keywords=&activity_type=&workout_type=&commute=&private_activities=&trainer=&gear=&search_session_id=fc095d51-c862-477b-954b-898f776a16ae&new_activity_only=false'
		response = self._session.get( url, params=parameters, headers=HEADERS_API )
		page = self._importer.load_as_activity( resource=Resource( content=response.content ) )

		return []

		# self.ctx.start( f'fetching activity summaries from {self.display_name}' )

		resources = []

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

# setup

INTRO_TEXT = f'GPX and TCX files from Strava will be downloaded via Strava\'s Web API, that\'s why your credentials are needed.'

@setup
def setup( ctx: ApplicationContext, config: Dict, state: Dict ) -> Tuple[Dict, Dict]:
	ctx.console.print( INTRO_TEXT, width=120 )

	username = Prompt.ask( 'Enter your user name', console=ctx.console, default=config.get( 'username', '' ) )
	password = Prompt.ask( 'Enter your password', console=ctx.console, default=config.get( 'password' ), password=True )

	return { 'username': username, 'password': password }, {}

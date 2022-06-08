
from logging import getLogger
from re import match
from re import DOTALL
from sys import exit as sysexit
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Tuple

from bs4 import BeautifulSoup
from dateutil.parser import parse
from dateutil.tz import tzlocal
from requests import options
from requests import Session
from rich.prompt import Prompt

from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity_types import ActivityTypes
from ..base import Resource
from ..config import ApplicationConfig as cfg
from ..config import ApplicationConfig as state
from ..config import console
from ..config import APPNAME
from ..config import KEY_CLASSIFER
from ..config import KEY_METADATA
from ..config import KEY_PLUGINS
from ..config import KEY_RAW
from ..config import KEY_RESOURCES
from ..service import Service

log = getLogger( __name__ )

SERVICE_NAME = 'bikecitizens'
DISPLAY_NAME = 'Bike Citizens'

HEADERS_TEMPLATE = {
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'en-US,en;q=0.5',
	'Cache-Control': 'no-cache',
	'Connection': 'keep-alive',
	'DNT': '1',
	'Pragma': 'no-cache',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
}

HEADERS_LOGIN = { **HEADERS_TEMPLATE, **{
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
		'Content-Type': 'application/x-www-form-urlencoded',
		'Host': 'my.bikecitizens.net',
		'Origin': 'https://my.bikecitizens.net',
		'Referer': 'https://my.bikecitizens.net/users/sign_in',
		'TE': 'Trailers',
	}
}

HEADERS_OPTIONS = { **HEADERS_TEMPLATE, **{
		'Accept': '*/*',
		'Access-Control-Request-Method': 'GET',
		'Access-Control-Request-Headers': 'x-api-key',
		'Host': 'api.bikecitizens.net',
		'Referer': 'https://my.bikecitizens.net/',
		'Origin': 'https://my.bikecitizens.net',
		'Sec-Fetch-Dest': 'empty',
		'Sec-Fetch-Mode': 'cors',
		'Sec-Fetch-Site': 'same-site'
	}
}

@document
class BikecitizensActivity( Activity ):

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.raw:
			self.raw_id = self.raw.get( 'id', 0 )
			self.type = ActivityTypes.bike
			self.average_speed = self.raw.get( 'average_speed' )
			self.cccode = self.raw.get( 'cccode' )
			self.distance = self.raw.get( 'distance' )
			self.duration = self.raw.get( 'duration' )
			self.time = parse( self.raw['start_time'] )
			self.localtime = parse( self.raw['start_time'] ).astimezone( tzlocal() )
			self.tags = self.raw.get( 'tags' )
			self.uuid = self.raw.get( 'uuid' )

		self.classifier = SERVICE_NAME
		self.uid = f'{SERVICE_NAME}:{self.raw_id}'

@service
class Bikecitizens( Service, Plugin ):

	def __init__( self, base_url=None, api_url=None, user_id=None, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )

		self._base_url = base_url if base_url else 'https://my.bikecitizens.net'
		self._api_url = api_url if api_url else 'https://api.bikecitizens.net'
		self._user_id = user_id

		self._signin_url = f'{self._base_url}/users/sign_in'
		self._user_url = f'{self.api_url}/api/v1/users/{self._user_id}'

		self._session = None
		self._api_key = None

		#self.api_url = 'https://api.bikecitizens.net/api/v1/users'
		#self.stats_url = 'https://api.bikecitizens.net/api/v1/users/{user}/stats?start={year}-01-01&end={year}-12-31'
		#self._stats_url = self._api_url + '/api/v1/users/{user}/stats?start={year}-01-01&end={year}-12-31'

	# service urls

	@property
	def base_url( self ) -> str:
		return self._base_url

	@base_url.setter
	def base_url( self, url: str ) -> None:
		self._base_url = url
		self._signin_url = f'{self.base_url}/users/sign_in'
		self._user_url = f'{self.api_url}/api/v1/users/{self._user_id}'

	@property
	def api_url( self ) -> str:
		return self._api_url

	@api_url.setter
	def api_url( self, url: str ) -> None:
		self._api_url = url

	# sample:
	# f'https://api.bikecitizens.net/api/v1/users/{user_id}/stats?start=2010-01-01&end=2022-12-31'
	def stats_url( self, year: int ) -> str:
		return f'{self._user_url}/stats?start={year}-01-01&end={year}-12-31'

	# service methods

	def login( self ) -> bool:
		if not self._session:
			self._session = Session()

		# session restore does not yet work
		#		if self.name in self._state:
		#			self._session.cookies.set( "api_key", self._state[self.name]['api_key'], domain="my.bikecitizens.net" )
		#			self._session.cookies.set( "_dashboard_session", self._state[self.name]['session'], domain="my.bikecitizens.net" )
		#			return True

		response = self._session.get( self._signin_url )

		try:
			token = BeautifulSoup( response.text, 'html.parser' ).find( 'input', attrs={ 'name': 'authenticity_token' } )['value']
		except TypeError:
			token = None

		if token is None:
			log.error( f"Unable to find authenticity token for {self.name}" )
			return False
		else:
			log.debug( f"Found authenticity token for {self.name}: {token}" )

		if not self.cfg_value( 'username' ) and not self.cfg_value( 'password' ):
			log.error( f'application setup not complete for {self.display_name}, consider running {APPNAME} setup' )
			sysexit( -1 )

		data = {
			'utf8': '✓',
			'authenticity_token': token,
			'user[login]': self.cfg_value( 'username' ),
			'user[password]': self.cfg_value( 'password' ),
			'commit': 'Login'
		}

		response = self._session.post( self._signin_url, headers=HEADERS_LOGIN, data=data )

		# status should be 200, need to check what is returned if credentials are wrong
		if response.status_code == 200:
			state[KEY_PLUGINS][SERVICE_NAME]['session'] = self._session.cookies['_dashboard_session']
			state[KEY_PLUGINS][SERVICE_NAME]['api_key'] = self._session.cookies['api_key']
		else:
			log.error( f'Login to {self.name} failed' )
			return False

		response = self._session.get( self.base_url )

		try:
			scripts = BeautifulSoup( response.text, 'html.parser' ).find_all( 'script' )
			for script in scripts:
				if m := match( r'.*\"id\":\s*\"(\d*)\".*', script.text, flags=DOTALL ):
					self._user_id = int( m.group( 1 ) )
		except TypeError:
			pass

		if 'api_key' in self._session.cookies:
			self._api_key = self._session.cookies['api_key']
		else:
			log.error( f'Unable to find api key for {self.name}' )
			return False

		if self._user_id is None:
			log.error( f'Unable to find user id for {self.name}' )
			return False

		return True

	def _fetch( self, year: int ) -> Iterable[Activity]:
		url = f'https://api.bikecitizens.net/api/v1/tracks/user/{self._user_id}'
		# noinspection PyUnusedLocal
		response = options( url, headers=HEADERS_OPTIONS )
		response = self._session.get( url, headers={ **HEADERS_OPTIONS, **{ 'X-API-Key': self._api_key } } )
		return [ Activity( self._prototype( j ), 0, self.name ) for j in response.json() ]

	def _prototype( self, json ) -> Mapping:
		resources = []
		for key in ['json', 'gpx']:
			resource = {
				'name': None,
				'type': key,
				'path': f"{json['id']}.{key}",
				'status': 100
			}
			resources.append( resource )
		mapping = {
			KEY_CLASSIFER: self.name,
			KEY_METADATA: {},
			KEY_RESOURCES: resources,
			KEY_RAW: { **json }
		}
		return mapping

	def _download_file( self, activity: Activity, resource: Resource ) -> Tuple[Any, int]:
		url = self.export_url( activity.raw_id, resource.type )
		log.debug( f'attempting download from {url}' )

		# noinspection PyUnusedLocal
		response = options( url, headers=HEADERS_OPTIONS )
		response = self._session.get( url, headers={ **HEADERS_OPTIONS, **{ 'X-API-Key': self._api_key } } )
		return response.content, response.status_code

	# noinspection PyMethodMayBeStatic
	def export_url( self, raw_id: int, ext: str ) -> str:
		if ext == 'gpx':
			url = f"https://api.bikecitizens.net/api/v1/tracks/{raw_id}/gpx"
		elif ext == 'json':
			url = f"https://api.bikecitizens.net/api/v1/tracks/{raw_id}/points"
		else:
			raise RuntimeError( 'unsupported resource type' )
		return url

	def setup( self ) -> None:
		console.print( f'For Bikecitizens we will use their Web API to download activity data, that\'s why your credentials are needed.' )

		user = Prompt.ask( 'Enter your user name', default=self.cfg_value( 'username' ) or '' )
		pwd = Prompt.ask( 'Enter your password', default=self.cfg_value( 'password' ) or '', password=True )

		cfg[KEY_PLUGINS][self._name]['username'] = user
		cfg[KEY_PLUGINS][self._name]['password'] = pwd

	def setup_complete( self ) -> bool:
		pass
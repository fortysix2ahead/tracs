
from logging import getLogger
from pathlib import Path
from re import match
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Tuple

from requests import Session
from sys import exit as sysexit
from time import time as current_time

from bs4 import BeautifulSoup
from click import echo
from dateutil.parser import parse
from dateutil.tz import tzlocal
from dateutil.tz import UTC
from rich.prompt import Prompt

from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity_types import ActivityTypes
from ..activity_types import ActivityTypes as Types
from ..base import Resource
from ..config import ApplicationConfig as cfg
from ..config import console
from ..config import APPNAME
from ..config import KEY_CLASSIFER
from ..config import KEY_METADATA
from ..config import KEY_PLUGINS
from ..config import KEY_RAW
from ..config import KEY_RESOURCES
from ..service import Service
from ..utils import seconds_to_time as stt

log = getLogger( __name__ )

# general purpose fields/headers/type definitions

SERVICE_NAME = 'polar'
DISPLAY_NAME = 'Polar Flow'

HEADERS_LOGIN = {
	'Accept': '*/*',
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'en-US,en;q=0.5',
	'Cache-Control': 'no-cache',
	'Connection': 'keep-alive',
	'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
	'DNT': '1',
	'Host': 'flow.polar.com',
	'Origin': 'https://flow.polar.com',
	'Pragma': 'no-cache',
	'Referer': 'https://flow.polar.com/',
	'TE': 'Trailers',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
	# 'X-Requested-With': 'XMLHttpRequest'
}
HEADERS_API = {
	'Accept': 'application/json',
	'Accept-Encoding': 'gzip, deflate, br',
	'Cache-Control': 'no-cache',
	'Connection': 'keep-alive',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'
}
HEADERS_DOWNLOAD = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'de,en;q=0.7,en-US;q=0.3',
	'Cache-Control': 'no-cache',
	'Connection': 'keep-alive',
	'DNT': '1',
	'Host': 'flow.polar.com',
	# 'Referer': 'https://flow.polar.com/training/analysis/{polar_id}',
	'TE': 'Trailers',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
	# 'X-Requested-With': 'XMLHttpRequest'
}

# all types: https://www.polar.com/accesslink-api/#detailed-sport-info-values-in-exercise-entity
# this maps the last part of the icon URL to Polar sports types, there's no other way to find the actual type
# example: iconUrl = "https://platform.cdn.polar.com/ecosystem/sport/icon/808d0882e97375e68844ec6c5417ea33-2015-10-20_13_46_22
TYPES = {
	'003304795bc33d808ee8e6ab8bf45d1f-2015-10-20_13_45_17': Types.triathlon,
	'20951a7d8b02def8265f5231f57f4ed9-2015-10-20_13_45_40': Types.multisport,
	'22f701a2c43d7c5678140b0a3e52ddaa-2015-10-20_13_46_02': Types.rollski_classic,
	'2524f40bcd8372f0912cb213c1fc9a29-2015-10-20_13_45_29': Types.bike_road,
	'3c1103ccbeee33fa663a1dc8e0fd8a6d-2015-10-20_13_45_48': Types.xcski_classic,
	'3e8556e6cf6ed3f01e5f8af133117416-2015-10-20_13_46_00': Types.rollski_free,
	'40894732d0b606b3fd9c9c34471df222-2015-10-20_13_46_28': Types.swim_indoor,
	'49b881c0a9aec1fce68fab11f8f1b01d-2016-02-03_06_06_42': Types.gymnastics,
	'4c54b3b02bd2d8b9b3f60931776a3497-2015-10-20_13_46_07': Types.unknown,
	'4ddd474b10302e72fb53bbd69028e15b-2015-10-20_13_46_17': Types.bike_mountain,
	'561a80f6d7eef7cc328aa07fe992af8e-2015-10-20_13_46_03': Types.bike,
	'5cdfcd252814f732414d977484cef4ea-2015-10-20_13_46_11': Types.swim_outdoor,
	'808d0882e97375e68844ec6c5417ea33-2015-10-20_13_46_22': Types.run,
	'9e3fc7036226634543f971acd1a68e60-2015-11-25_10_37_05': Types.ergo,
	'a2afcae540681c227a48410d97277e2e-2015-10-20_13_45_18': Types.unknown,
	'a2e8c7a794dadb60ecbfb21239f5b981-2016-02-03_06_06_32': Types.unknown,
	'd1ce94078aec226be28f6c602e6803e1-2015-10-20_13_45_19': Types.gym,
	'e25370188b9c9b611dcafb6f0028faeb-2015-10-20_13_45_32': Types.hike,
	'f0c9643f1cef947e5621b0b46ab06783-2015-10-20_13_46_12': Types.xcski_free,
	'f4197b0c1a4d65962b9e45226c77d4d5-2015-10-20_13_45_26': Types.swim,
}

@document
class PolarActivity( Activity ):

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.raw:
			self.raw_id = _raw_id( self.raw )
			self.name = self.raw.get( 'title' )
			self.type = _type_of( self.raw )
			# self.event_type = self.raw.get( 'eventType' )
			self.time = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC )
			self.localtime = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() )
			self.distance = self.raw.get( 'distance' )
			self.duration = stt( self.raw['duration'] / 1000 ) if self.raw.get( 'duration' ) else None
			self.calories = self.raw.get( 'calories' )

		self.classifier = SERVICE_NAME
		self.uid = f'{SERVICE_NAME}:{self.raw_id}'

@service
class Polar( Service, Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self.base_url = 'https://flow.polar.com'
		self._session = None

	def path_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		path = super().path_for( a, ext )
		if a.is_multipart:
			path = Path( super().path_for( a ), f'{id}.{ext}.zip' ) if ext in ['gpx', 'tcx', 'hrv'] else None

		return path

	def _link_path( self, pa: Activity, ext: str ) -> Path or None:
		if pa.id:
			utc = pa.utctime
			parent = Path( self._lib_dir, utc.strftime( '%Y/%m/%d' ) )
			#a = self.db.get_activity( pa )
			#if a and a.name:
			#	return Path( parent, f'{utc.strftime( "%H%M%S" )} - {a.name}.polar.{ext}' )  # fully qualified path
			#else:
			return Path( parent, f'{utc.strftime( "%H%M%S" )}.{self.name}.{ext}' )  # fully qualified path
		else:
			return None

	@property
	def base_url( self ) -> str:
		return self._url_base

	@base_url.setter
	def base_url( self, url: str ) -> None:
		self._url_base = url
		self._url_login = f'{self._url_base}/login'
		self._url_ajax_login = f'{self._url_base}/ajaxLogin?_={str( int( current_time() ) )}'
		self._url_events = f'{self._url_base}/training/getCalendarEvents'
		self._url_export = f'{self._url_base}/api/export/training'

	@property
	def login_url( self ) -> str:
		return f'{self.base_url}/login'

	@property
	def login_ajax_url( self ) -> str:
		return  f'{self.base_url}/ajaxLogin?_={str( int( current_time() ) )}'

	@property
	def events_url( self ) -> str:
		return f'{self.base_url}/training/getCalendarEvents'

	@property
	def export_url( self ) -> str:
		return f'{self.base_url}/api/export/training'

	@property
	def url_export( self ) -> str:
		return self._url_export

	def url_export_for( self, id: int, ext: str ) -> str:
		if ext == 'gpx':
			return f'{self._url_export}/gpx/{id}'
		elif ext == 'tcx':
			return f'{self._url_export}/tcx/{id}'
		elif ext == 'csv':
			return f'{self._url_export}/csv/{id}'
		elif ext == 'hrv':
			return f'{self._url_export}/rr/csv/{id}'
		else:
			return ''

	def url_events_year( self, year ) -> str:
		return f'{self._url_events}?start=1.1.{year}&end=31.12.{year}'

	def url_activity( self, id: int ) -> str:
		return f'{self._url_base}/training/analysis/{id}'

	def login( self ) -> bool:
		if not self._session:
			self._session = Session()

		# noinspection PyUnusedLocal
		response = self._session.get( self._url_base )
		response = self._session.get( self._url_ajax_login )

		try:
			token = BeautifulSoup( response.text, 'html.parser' ).find( 'input', attrs={ 'name': 'csrfToken' } )['value']
		except TypeError:
			token = None

		log.debug( f"CSRF Token: {token}" )

		if token is None:
			echo( "CSRF Token not found" )
			return False

		if not self.cfg_value( 'username' ) and not self.cfg_value( 'password' ):
			log.error( f"application setup not complete for Polar Flow, consider running {APPNAME} setup" )
			sysexit( -1 )

		data = {
			'csrfToken': token,
			'email': self.cfg_value( 'username' ),
			'password': self.cfg_value( 'password' ),
			'returnUrl': '/'
		}

		# noinspection PyUnusedLocal
		response = self._session.post( self._url_login, headers=HEADERS_LOGIN, data=data )

		self._logged_in = True
		return self._logged_in

	def _fetch( self, year: int ) -> Iterable[Activity]:
		json = self._session.get( self.url_events_year( year ), headers=HEADERS_API ).json()
		return [ Activity( self._prototype( j ), 0, self.name ) for j in json ]

	def _prototype( self, json ) -> Mapping:
		resources = []
		id = _raw_id( json )
		for key in ['csv', 'gpx', 'hrv', 'tcx']:
			resource = {
				'name': None,
				'type': key,
				'path': f'{id}.{key}.csv' if key == 'hrv' else f'{id}.{key}',
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
		url = self.url_export_for( activity.raw_id, resource.type )
		log.debug( f'attempting download from {url}' )

		response = self._session.get( url, headers=HEADERS_DOWNLOAD, allow_redirects=True, stream=True )
		return response.content, response.status_code

	def _download_multipart_file( self, pa: Activity, ext: str ) -> None:
		if not (url := pa.export_file_url( ext )):  # skip download for csv files
			return

		response = self._session.get( url, headers=HEADERS_DOWNLOAD, allow_redirects=True, stream=True )

		if response.status_code == 200:
			if len( response.content ) > 0:
				zipfile = self._path( pa, ext )
				zipfile.parent.mkdir( parents=True, exist_ok=True )
				zipfile.write_bytes( response.content )
				pa.metadata[ext] = 200
				log.info( f"downloaded {ext} for polar multipart activity {pa.id}" )
			else:
				pa.metadata[ext] = 204
				log.error( f"failed to download {ext} for polar multipart activity {pa.id}, service responded with 204" )
		else:
			pa.metadata[ext] = 404
			log.error( f"failed to download {ext} for polar multipart activity {pa.id}, service responded with 404" )

		self._db.update( self.name, dict( pa ), pa.doc_id )

	def setup( self ) -> None:
		console.print( f'For Polar Flow we will use their inofficial Web API to download activity data, that\'s why your credentials are needed.' )

		user = Prompt.ask( 'Enter your user name', default=self.cfg_value( 'username' ) or '' )
		pwd = Prompt.ask( 'Enter your password', default=self.cfg_value( 'password' ) or '', password=True )

		cfg[KEY_PLUGINS][SERVICE_NAME]['username'] = user
		cfg[KEY_PLUGINS][SERVICE_NAME]['password'] = pwd

	def setup_complete( self ) -> bool:
		if self.cfg_value( 'username' ) and self.cfg_value( 'password' ):
			return True
		else:
			return False

# --- helper

def _raw_id( r: Mapping ) -> int:
	r = r or {}
	eventType = r.get( 'eventType' )
	if eventType == 'exercise' or eventType == 'fitnessData':
		return r.get( 'listItemId' )
	elif eventType == 'orthostaticTest':
		return int( match( '.*id=(\d+).*', r.get( 'url', '' ) )[1] )
	elif eventType == 'rrTest':
		return int( match( '.*/rr/(\d+)', r.get( 'url', '' ) )[1] )
	return 0

def _type_of( r: Mapping ) -> ActivityTypes:
	if 'iconUrl' not in r:
		return Types.unknown
	id = r.get( 'iconUrl' ).rsplit( '/', 1 )[1]
	return TYPES.get( id, Types.unknown )

def _is_multipart( self ) -> bool:
	# polar icons for identifying multipart activities: there does not seem to be any other way to identify those
	POLAR_TRIATHLON = '003304795bc33d808ee8e6ab8bf45d1f-2015-10-20_13_45_17'
	POLAR_MULTISPORT = '20951a7d8b02def8265f5231f57f4ed9-2015-10-20_13_45_40'
	iconUrl = self.get( 'iconUrl', '' )
	return True if iconUrl.endswith( POLAR_TRIATHLON ) or iconUrl.endswith( POLAR_MULTISPORT ) else False

def _multipart_str( self ) -> str:
	if self.multipart:
		return '\u2705'
	else:
		return '\u2716'

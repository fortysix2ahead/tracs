
from datetime import datetime
from logging import getLogger
from pathlib import Path
from re import match
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from requests import Session
from sys import exit as sysexit
from time import time as current_time

from bs4 import BeautifulSoup
from click import echo
from dateutil.parser import parse
from dateutil.tz import tzlocal
from dateutil.tz import UTC
from orjson import dumps as dump_json, OPT_INDENT_2, OPT_APPEND_NEWLINE
from rich.prompt import Prompt

from . import Registry
from . import document
from . import importer
from . import service
from .handlers import GPX_TYPE
from .handlers import JSON_TYPE
from .handlers import TCX_TYPE
from .handlers import JSONHandler
from .handlers import ResourceHandler
from .handlers import XML_TYPE
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
from ..activity_types import ActivityTypes
from ..activity_types import ActivityTypes as Types
from ..base import Importer
from ..config import ApplicationConfig as cfg
from ..config import console
from ..config import APPNAME
from ..config import KEY_PLUGINS
from ..service import Service
from ..utils import seconds_to_time as stt

log = getLogger( __name__ )

# general purpose fields/headers/type definitions

SERVICE_NAME = 'polar'
DISPLAY_NAME = 'Polar Flow'
ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2

POLAR_CSV_TYPE = 'text/csv+polar'
POLAR_HRV_TYPE = 'text/csv+polar-hrv'
POLAR_FLOW_TYPE = 'application/json+polar'
POLAR_EXERCISE_DATA_TYPE = 'application/xml+polar-ped'
PED_NS = 'http://www.polarpersonaltrainer.com'

BASE_URL = 'https://flow.polar.com'

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

	def __post_init__( self ):
		super().__post_init__()

		if self.raw:
			self.raw_id = _raw_id( self.raw )
			self.name = self.raw.get( 'title' )
			self.type = _type_of( self.raw )
			self.time = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC )
			self.localtime = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() )
			self.distance = self.raw.get( 'distance' )
			self.duration = stt( self.raw['duration'] / 1000 ) if self.raw.get( 'duration' ) else None
			self.calories = self.raw.get( 'calories' )

		self.uid = f'{SERVICE_NAME}:{self.raw_id}'

@document
class PolarExerciseDataActivity( Activity ):
	def __post_init__( self ):
		super().__post_init__()

		if self.raw:
			self.classifier = 'polar'
			self.time = datetime.strptime( self.raw.get( 'time' ), '%Y-%m-%d %H:%M:%S.%f' ).astimezone( UTC )  # 2016-09-15 16:50:27.0
			self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )
			self.uid = f'{self.classifier}:{self.raw_id}'

@importer( type=POLAR_FLOW_TYPE )
class PolarImporter( ResourceHandler ):

	json_handler = Registry.importer_for( JSON_TYPE )

	def load_data( self, data: Any, **kwargs ) -> Any:
		return PolarImporter.json_handler.load( data=data )

	def postprocess_data( self, structured_data: Any, loaded_data: Any, path: Optional[Path], url: Optional[str] ) -> Any:
		resource = Resource( type=POLAR_FLOW_TYPE, path=path.name, source=path.as_uri(), status=200, raw=structured_data, raw_data=loaded_data )
		activity = PolarActivity( raw=structured_data, resources=[resource] )
		return activity

@importer( type=POLAR_EXERCISE_DATA_TYPE )
class PersonalTrainerImporter( ResourceHandler ):

	xml_handler = Registry.importer_for( XML_TYPE )

	def load_path( self, path: Path, **kwargs ) -> Optional[Union[str, bytes]]:
		return PersonalTrainerImporter.xml_handler.load( path=path, **kwargs )

	def load_data( self, data: Any, **kwargs ) -> Any:
		structured_data = {
			'time': data.getroot().find( self._ns( 'calendar-items/exercise/time' ) ).text,
			'type': data.getroot().find( self._ns( 'calendar-items/exercise/sport' ) ).text,
			'result_type': data.getroot().find( self._ns( 'calendar-items/exercise/sport-results/sport-result/sport' ) ).text, # should be the same as type
			'duration': data.getroot().find( self._ns( 'calendar-items/exercise/sport-results/sport-result/duration' ) ).text, # should be the same as type
			'distance': data.getroot().find( self._ns( 'calendar-items/exercise/sport-results/sport-result/distance' ) ).text,
			'calories': data.getroot().find( self._ns( 'calendar-items/exercise/sport-results/sport-result/calories' ) ).text,
			'recording_rate': data.getroot().find( self._ns( 'calendar-items/exercise/sport-results/sport-result/recording-rate' ) ).text,
		}
		samples = data.getroot().findall( self._ns( 'calendar-items/exercise/sport-results/sport-result/samples/sample' ) )
		for s in samples:
			sample_type = s.find( self._ns( 'type' ) ).text
			sample_values = s.find( self._ns( 'values' ) ).text
			structured_data[('samples', sample_type)] = sample_values.split( ',' )
		return structured_data

	def _activity_cls_type( self ) -> Optional[Tuple[Type, str]]:
		return PolarExerciseDataActivity, POLAR_EXERCISE_DATA_TYPE

	def _ns( self, s: str ):
		return f'{{{PED_NS}}}' + s.replace( '/', f'/{{{PED_NS}}}' )

@service
class Polar( Service, Plugin ):

	def __init__( self, base_url=None, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self.base_url = base_url
		self._session = None

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		return super().path_for( activity, resource, ext )
		# if a.is_multipart: # todo: add multipart support
		#	 path = Path( super().path_for( a ), f'{id}.{ext}.zip' ) if ext in ['gpx', 'tcx', 'hrv'] else None

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
		return self._base_url

	@base_url.setter
	def base_url( self, url: str ) -> None:
		self._base_url = url if url else BASE_URL
		self._login_url = f'{self._base_url}/login'
		self._ajax_login_url = f'{self._base_url}/ajaxLogin?_={str( int( current_time() ) )}'
		self._events_url = f'{self._base_url}/training/getCalendarEvents'
		self._activity_url = f'{self._base_url}/training/analysis'
		self._export_url = f'{self._base_url}/api/export/training'

	@property
	def ajax_login_url( self ) -> str:
		return  f'{self.base_url}/ajaxLogin?_={str( int( current_time() ) )}'

	def events_url_for( self, year ) -> str:
		return f'{self._events_url}?start=1.1.{year}&end=31.12.{year}'

	def all_events_url( self ):
		return f'{self._events_url}?start=1.1.1970&end=1.1.{datetime.utcnow().year + 1}'

	def url_for( self, id: Union[int,str], type: str ):
		if type == POLAR_CSV_TYPE:
			return f'{self._export_url}/csv/{id}'
		elif type == GPX_TYPE:
			return f'{self._export_url}/gpx/{id}'
		elif type == TCX_TYPE:
			return f'{self._export_url}/tcx/{id}'
		elif type == POLAR_HRV_TYPE:
			return f'{self._export_url}/rr/csv/{id}'

	def export_url_for( self, id: int, ext: str ) -> str:
		return f'{self._export_url}/rr/csv/{id}' if ext == 'hrv' else f'{self._export_url}/{ext}/{id}'

	def activity_url( self, id: int ) -> str:
		return f'{self._activity_url}/{id}'

	def login( self ) -> bool:
		if self.logged_in and self._session:
			return self.logged_in

		if not self._session:
			self._session = Session()

		# noinspection PyUnusedLocal
		response = self._session.get( self.base_url )
		response = self._session.get( self.ajax_login_url )

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
		response = self._session.post( self._login_url, headers=HEADERS_LOGIN, data=data )

		self._logged_in = True
		return self._logged_in

	def _fetch( self, force: bool = False, **kwargs ) -> Iterable[Activity]:
		events_url = self.all_events_url()
		response = self._session.get( events_url, headers=HEADERS_API)
		return [ self._prototype( response.content, json ) for json in response.json() ]

	# noinspection PyMethodMayBeStatic
	def _prototype( self, content, json ) -> PolarActivity:
		raw_id = _raw_id( json )
		uid = f'{self.name}:{raw_id}'
		# json_str = dump_json( json, option=ORJSON_OPTIONS )
		resources = [
			Resource( type=POLAR_FLOW_TYPE, path=f"{raw_id}.raw.json", status=200, uid=uid, raw=json, raw_data=content, source=self.activity_url( raw_id ) ),
			Resource( type=POLAR_CSV_TYPE, path=f'{raw_id}.csv', status=100, uid=uid, source=self.url_for( raw_id, POLAR_CSV_TYPE ) ),
			Resource( type=GPX_TYPE, path=f'{raw_id}.gpx', status=100, uid=uid, source=self.url_for( raw_id, GPX_TYPE ) ),
			Resource( type=TCX_TYPE, path=f'{raw_id}.tcx', status=100, uid=uid, source=self.url_for( raw_id, TCX_TYPE ) ),
			Resource( type=POLAR_HRV_TYPE, path=f'{raw_id}.hrv.csv', status=100, uid=uid, source=self.url_for( raw_id, POLAR_HRV_TYPE ) )
		]
		return PolarActivity( raw=json, resources=resources )

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		url = self.url_for( resource.raw_id(), resource.type )
		if url:
			log.debug( f'downloading resource from {url}' )
			response = self._session.get( url, headers=HEADERS_DOWNLOAD, allow_redirects=True, stream=True )
			return response.content, response.status_code
		else:
			log.warning( f'unable to determine download url for resource {resource}' )
			return None, 500

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

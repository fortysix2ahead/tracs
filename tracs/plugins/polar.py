
from datetime import datetime
from logging import getLogger
from pathlib import Path
from re import match
from typing import Any
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Union

from requests_cache import CachedSession
from sys import exit as sysexit
from time import time as current_time

from bs4 import BeautifulSoup
from click import echo
from dateutil.parser import parse
from dateutil.tz import tzlocal
from dateutil.tz import UTC
from fs import open_fs
from fs.zipfs import ReadZipFS
from rich.prompt import Prompt

from . import Registry
from . import document
from . import importer
from . import service
from tracs.plugins.gpx import GPX_TYPE
from .handlers import JSONHandler
from .handlers import TCX_TYPE
from .handlers import XMLHandler
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
from ..activity_types import ActivityTypes
from ..activity_types import ActivityTypes as Types
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

POLAR_CSV_TYPE = 'text/csv+polar'
POLAR_HRV_TYPE = 'text/csv+polar-hrv'
POLAR_FLOW_TYPE = 'application/json+polar'
POLAR_EXERCISE_DATA_TYPE = 'application/xml+polar-ped'
POLAR_ZIP_GPX_TYPE = 'application/zip+polar-gpx'
POLAR_ZIP_TCX_TYPE = 'application/zip+polar-tcx'
PED_NS = 'http://www.polarpersonaltrainer.com'

# polar icon ids for identifying multipart activities: there does not seem to be any other way to identify those
ICON_ID_TRIATHLON = '003304795bc33d808ee8e6ab8bf45d1f-2015-10-20_13_45_17' # triathlon
ICON_ID_MULTISPORT ='20951a7d8b02def8265f5231f57f4ed9-2015-10-20_13_45_40' # multisport

BASE_URL = 'https://flow.polar.com'

HEADERS_TEMPLATE = {
	'Accept-Encoding': 'gzip, deflate, br',
	'Accept-Language': 'en-US,en;q=0.5',
	'Connection': 'keep-alive',
	'DNT': '1',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
}

HEADERS_LOGIN = { **HEADERS_TEMPLATE, **{
	'Accept': '*/*',
	'Cache-Control': 'no-cache',
	'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
	'Host': 'flow.polar.com',
	'Origin': 'https://flow.polar.com',
	'Pragma': 'no-cache',
	'Referer': 'https://flow.polar.com/',
	'TE': 'Trailers',
	# 'X-Requested-With': 'XMLHttpRequest'
} }

HEADERS_API = { **HEADERS_TEMPLATE, **{
	'Accept': 'application/json',
	# 'Cache-Control': 'no-cache',
} }

HEADERS_DOWNLOAD = { **HEADERS_TEMPLATE, **{
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	# 'Cache-Control': 'no-cache',
	'Host': 'flow.polar.com',
	# 'Referer': 'https://flow.polar.com/training/analysis/{polar_id}',
	'TE': 'Trailers',
	# 'X-Requested-With': 'XMLHttpRequest'
} }

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

@document( type=POLAR_FLOW_TYPE )
class PolarActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		self.raw_id = _raw_id( self.raw )
		self.uid = f'{SERVICE_NAME}:{self.raw_id}'

		self.name = self.raw.get( 'title' )
		self.type = _type_of( self.raw )
		self.time = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC )
		self.localtime = parse( self.raw['datetime'], ignoretz=True ).replace( tzinfo=tzlocal() )
		self.distance = self.raw.get( 'distance' )
		self.duration = stt( self.raw['duration'] / 1000 ) if self.raw.get( 'duration' ) else None
		self.calories = self.raw.get( 'calories' )

@document
class PolarExerciseDataActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		self.classifier = 'polar'
		self.time = datetime.strptime( self.raw.get( 'time' ), '%Y-%m-%d %H:%M:%S.%f' ).astimezone( UTC )  # 2016-09-15 16:50:27.0
		self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )
		self.uid = f'{self.classifier}:{self.raw_id}'

@importer( type=POLAR_FLOW_TYPE )
class PolarImporter( JSONHandler ):

	def __init__( self ) -> None:
		super().__init__( type=POLAR_FLOW_TYPE, activity_cls=PolarActivity )

@importer( type=POLAR_EXERCISE_DATA_TYPE )
class PersonalTrainerImporter( XMLHandler ):

	def __init__( self ) -> None:
		super().__init__( type=POLAR_EXERCISE_DATA_TYPE, activity_cls=PolarExerciseDataActivity )

	def postprocess_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		xml = super().postprocess_data( data, text, content, path, url )
		root = xml.getroot()
		data = {
			'time': root.find( self._ns( 'calendar-items/exercise/time' ) ).text,
			'type': root.find( self._ns( 'calendar-items/exercise/sport' ) ).text,
			'result_type': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/sport' ) ).text, # should be the same as type
			'duration': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/duration' ) ).text, # should be the same as type
			'distance': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/distance' ) ).text,
			'calories': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/calories' ) ).text,
			'recording_rate': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/recording-rate' ) ).text,
		}
		samples = root.findall( self._ns( 'calendar-items/exercise/sport-results/sport-result/samples/sample' ) )
		for s in samples:
			sample_type = s.find( self._ns( 'type' ) ).text
			sample_values = s.find( self._ns( 'values' ) ).text
			data[('samples', sample_type)] = sample_values.split( ',' )
		return data

	# noinspection PyMethodMayBeStatic
	def _ns( self, s: str ):
		return f'{{{PED_NS}}}' + s.replace( '/', f'/{{{PED_NS}}}' )

@service
class Polar( Service, Plugin ):

	def __init__( self, base_url=None, **kwargs ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )
		self.base_url = base_url # use setter in order to update all internal fields
		self._session = None
		self._logged_in = False

		self.importer: PolarImporter = Registry.importer_for( POLAR_FLOW_TYPE )

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

	def url_for_id( self, local_id: Union[int, str] ) -> str:
		return f'{self._activity_url}/{local_id}'

	def url_for_resource_type( self, local_id: Union[int, str], type: str ):
		url = None

		if type == POLAR_CSV_TYPE:
			url = f'{self._export_url}/csv/{local_id}'
		elif type == GPX_TYPE:
			url = f'{self._export_url}/gpx/{local_id}'
		elif type == TCX_TYPE:
			url = f'{self._export_url}/tcx/{local_id}'
		elif type == POLAR_HRV_TYPE:
			url = f'{self._export_url}/rr/csv/{local_id}'
		elif type == POLAR_ZIP_GPX_TYPE:
			url = f'{self._export_url}/gpx/{local_id}?compress=true'
		elif type == POLAR_ZIP_TCX_TYPE:
			url = f'{self._export_url}/tcx/{local_id}?compress=true'

		return url

	def login( self ) -> bool:
		if self._logged_in and self._session:
			return self._logged_in

		if not self._session:
			self._session = CachedSession( backend='memory' )

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

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		if not self.login():
			return []

		try:
			response = self._session.get( self.all_events_url(), headers=HEADERS_API )
			resources = []

			for json in response.json():
				resource = self.importer.load( data=json, as_resource=True )
				local_id = _local_id( json )
				resource.uid = f'{self.name}:{local_id}'
				resource.path = f'{local_id}.raw.json'
				resource.status = 200
				resource.source = self.url_for_id( local_id )
				resource.summary = True
				resource.text = self.importer.save_data( json )

				resources.append( resource )

			return resources

		except RuntimeError:
			log.error( f'error fetching activity ids' )
			return []

	def download( self, activity: Optional[Activity] = None, summary: Optional[Resource] = None, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		try:
			lid = summary.raw_id
			uid = summary.uid

			if _is_multipart_id( summary.raw.get( 'iconUrl' ) ):
				resources = [
					Resource( type=POLAR_ZIP_GPX_TYPE, path=f'{lid}.gpx.zip', status=100, uid=uid, source=self.url_for_resource_type( lid, POLAR_ZIP_GPX_TYPE ) ),
					Resource( type=POLAR_ZIP_TCX_TYPE, path=f'{lid}.tcx.zip', status=100, uid=uid, source=self.url_for_resource_type( lid, POLAR_ZIP_TCX_TYPE ) ),
				]
			else:
				resources = [
					Resource( type=POLAR_CSV_TYPE, path=f'{lid}.csv', status=100, uid=uid, source=self.url_for_resource_type( lid, POLAR_CSV_TYPE ) ),
					Resource( type=GPX_TYPE, path=f'{lid}.gpx', status=100, uid=uid, source=self.url_for_resource_type( lid, GPX_TYPE ) ),
					Resource( type=TCX_TYPE, path=f'{lid}.tcx', status=100, uid=uid, source=self.url_for_resource_type( lid, TCX_TYPE ) ),
					Resource( type=POLAR_HRV_TYPE, path=f'{lid}.hrv.csv', status=100, uid=uid, source=self.url_for_resource_type( lid, POLAR_HRV_TYPE ) )
				]

			for r in resources:
				r.raw_data, r.status = self.download_resource( r )

			return resources

		except RuntimeError:
			log.error( f'error fetching resources' )
			return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		url = self.url_for_resource_type( resource.raw_id, resource.type )
		if url:
			log.debug( f'downloading resource from {url}' )
			response = self._session.get( url, headers=HEADERS_DOWNLOAD, allow_redirects=True, stream=True )
			return response.content, response.status_code
		else:
			log.warning( f'unable to determine download url for resource {resource}' )
			return None, 500

	def postprocess( self, activity: Optional[Activity], resources: Optional[List[Resource]], **kwargs ) -> None:
		for r in list( resources ):
			if r.type in [POLAR_ZIP_GPX_TYPE, POLAR_ZIP_TCX_TYPE]:
				activity.resources.extend( decompress_resources( r ) )

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

def _local_id( r: Mapping ) -> int:
	return _raw_id( r )

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

def _is_multipart_id( icon_url: str ) -> bool:
	return True if icon_url.endswith( ICON_ID_TRIATHLON ) or icon_url.endswith( ICON_ID_MULTISPORT ) else False

def _multipart_str( self ) -> str:
	if self.multipart:
		return '\u2705'
	else:
		return '\u2716'

def decompress_resources( r: Resource ) -> List[Resource]:
	mem_fs = open_fs('mem://')
	mem_fs.writebytes( '/archive.zip', r.content )
	resources = []

	with mem_fs.openbin( '/archive.zip' ) as zip_file:
		with ReadZipFS( zip_file ) as zip_fs:
			for f in zip_fs.listdir( '/' ):
				if f.endswith( '.gpx' ):
					resources.append( Resource( path=f, text=zip_fs.readtext( f'/{f}' ), type=GPX_TYPE, status=200, uid=r.uid, source=r.path ) )
				elif f.endswith( '.tcx' ):
					resources.append( Resource( path=f, text=zip_fs.readtext( f'/{f}' ), type=TCX_TYPE, status=200, uid=r.uid, source=r.path ) )

	return resources

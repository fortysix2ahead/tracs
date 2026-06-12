from datetime import datetime, time, timedelta
from itertools import zip_longest
from logging import getLogger
from pathlib import Path
from re import match
from sys import exit as sysexit
from time import time as current_time
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Union
from zipfile import BadZipFile

from bs4 import BeautifulSoup
from click import echo
from datetimerange import DateTimeRange
from dateutil.parser import parse
from dateutil.tz import tzlocal, UTC
from fs import open_fs
from fs.base import FS
from fs.errors import CreateFailed
from fs.zipfs import ReadZipFS
from requests_cache import CachedSession
from rich.prompt import Prompt

from tracs.activity import Activities, Activity
from tracs.activity_types import ActivityTypes
from tracs.aio import load_resource
from tracs.constants import APPNAME, CFG_CLASSIFIER
from tracs.pluginmgr import importer, resource_type, service, setup
from tracs.plugins.gpx import GPX_TYPE, GPXImporter
from tracs.plugins.json import DataclassFactoryHandler, JSONHandler
from tracs.plugins.polar.constants import *
from tracs.plugins.polar.io import PolarTrainingSessionImporter
from tracs.plugins.polar.models.flow import PolarFitnessTest, PolarFlowExercise, PolarOrthostaticTest, PolarRRRecording, ResourcePartlist
from tracs.plugins.polar_takeout import PolarFlowTakeoutImporter
from tracs.plugins.tcx import TCX_TYPE
from tracs.protocols import ApplicationContext
from tracs.resources import Resource, ResourceType
from tracs.service import Service
from tracs.uid import uid as uid_
from tracs.utils import seconds_to_time

log = getLogger( __name__ )

# general purpose fields/headers/type definitions

SERVICE_NAME = 'polar'
DISPLAY_NAME = 'Polar Flow'

PED_NS = 'http://www.polarpersonaltrainer.com'

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

@resource_type
def polar_resource_types() -> List[ResourceType]:
	return [
		ResourceType( name=POLAR_FLOW_TYPE, summary=True ),
		ResourceType( name=POLAR_FITNESS_TEST_TYPE ),
		ResourceType( name=POLAR_ORTHOSTATIC_TEST_TYPE ),
		ResourceType( name=POLAR_RRRECORDING_TYPE ),
		ResourceType( name=POLAR_CSV_TYPE ),
		ResourceType( name=POLAR_HRV_TYPE ),
		ResourceType( name=POLAR_SESSION_TYPE ),
		ResourceType( name=POLAR_EXERCISE_DATA_TYPE ),
	]

@importer
class PolarFlowImporter( DataclassFactoryHandler ):

	TYPE: str = POLAR_FLOW_TYPE
	ACTIVITY_CLS = PolarFlowExercise

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: PolarFlowExercise = resource.data
		return Activity(
			uid = f'{SERVICE_NAME}:{activity.local_id}',
			name = activity.title,
			type = activity.get_type(),
			starttime= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC ),
			starttime_local= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ),
			distance = activity.distance,
			duration = timedelta( seconds = activity.duration / 1000 ) if activity.duration else None,
			calories = activity.calories,
		)

@importer
class PolarFitnessTestImporter( DataclassFactoryHandler ):

	TYPE: str = POLAR_FITNESS_TEST_TYPE
	ACTIVITY_CLS = PolarFitnessTest

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: PolarFitnessTest = resource.data
		return Activity(
			uid = f'{SERVICE_NAME}:{activity.listItemId}',
			name = activity.title,
			type = ActivityTypes.test,
			starttime= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC ),
			starttime_local= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ),
		)

@importer
class PolarOrthostaticTestImporter( DataclassFactoryHandler ):

	TYPE: str = POLAR_ORTHOSTATIC_TEST_TYPE
	ACTIVITY_CLS = PolarOrthostaticTest

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: PolarOrthostaticTest = resource.data
		return Activity(
			uid = f'{SERVICE_NAME}:{activity.local_id}',
			name = activity.title,
			type = ActivityTypes.test,
			starttime= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC ),
			starttime_local= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ),
		)

@importer
class PolarRRRecordingImporter( DataclassFactoryHandler ):

	TYPE: str = POLAR_RRRECORDING_TYPE
	ACTIVITY_CLS = PolarRRRecording

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		activity: PolarRRRecording = resource.data
		return Activity(
			uid = f'{SERVICE_NAME}:{activity.local_id}',
			name = activity.title,
			type = ActivityTypes.test,
			starttime= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ).astimezone( UTC ),
			starttime_local= parse( activity.datetime, ignoretz=True ).replace( tzinfo=tzlocal() ),
		)

@service
class Polar( Service ):

	SERVICE_NAME: ClassVar[str] = SERVICE_NAME

	def __init__( self, **kwargs ):
		super().__init__( **kwargs )

		self._session = None
		self._logged_in = False

		self.importer: PolarFlowImporter = PolarFlowImporter()
		self._session_importer = PolarTrainingSessionImporter()
		self.take_importer: PolarFlowTakeoutImporter = PolarFlowTakeoutImporter()
		self.json_handler: JSONHandler = JSONHandler()
		self.gpx_importer = GPXImporter()

	def _link_path( self, pa: Activity, ext: str ) -> Path or None:
		if pa.id:
			utc = pa.utctime
			parent = Path( self._lib_dir, utc.strftime( '%Y/%m/%d' ) )
			# a = self.db.get_activity( pa )
			# if a and a.name:
			#	return Path( parent, f'{utc.strftime( "%H%M%S" )} - {a.name}.polar.{ext}' )  # fully qualified path
			# else:
			return Path( parent, f'{utc.strftime( "%H%M%S" )}.{self.name}.{ext}' )  # fully qualified path
		else:
			return None

	@property
	def login_url( self ) -> str:
		return f'{self.base_url}/login'

	@property
	def ajax_login_url( self ) -> str:
		return f'{self.base_url}/ajaxLogin?_={str( int( current_time() ) )}'

	@property
	def events_url( self ) -> str:
		return f'{self.base_url}/training/getCalendarEvents'

	@property
	def activity_url( self ) -> str:
		return f'{self.base_url}/training/analysis'

	@property
	def export_url( self ) -> str:
		return f'{self.base_url}/api/export/training'

	def events_url_for( self, range_from: datetime, range_to: datetime, year: Optional[int] = None ) -> str:
		if year:
			range_from, range_to = datetime( year, 1, 1 ), datetime( year, 12, 31 )
		if range_from and range_to:
			return f'{self.events_url}?start={range_from.strftime("%d.%m.%Y")}&end={range_to.strftime("%d.%m.%Y")}'
		else:
			return self.all_events_url()

	def all_events_url( self ):
		return f'{self.events_url}?start=1.1.1970&end=1.1.{datetime.utcnow().year + 1}'

	def url_for_id( self, local_id: Union[int, str] ) -> str:
		return f'{self.activity_url}/{local_id}'

	def url_for_resource_type( self, local_id: Union[int, str], type: str ):
		url = None

		if type == POLAR_CSV_TYPE:
			url = f'{self.export_url}/csv/{local_id}'
		elif type == GPX_TYPE:
			url = f'{self.export_url}/gpx/{local_id}'
		elif type == TCX_TYPE:
			url = f'{self.export_url}/tcx/{local_id}'
		elif type == POLAR_HRV_TYPE:
			url = f'{self.export_url}/rr/csv/{local_id}'
		elif type == POLAR_ZIP_GPX_TYPE:
			url = f'{self.export_url}/gpx/{local_id}?compress=true'
		elif type == POLAR_ZIP_TCX_TYPE:
			url = f'{self.export_url}/tcx/{local_id}?compress=true'

		return url

	# FS import
	def supports_fs_import( self, fs: FS | None, path: str | None ) -> bool:
		return any ( [ f for f in fs.walk.files( '/', filter=[ ACCOUNT_PROFILE_GLOB ] ) ] )

	def import_from_fs( self, src_fs: FS, dest_fs: FS, **kwargs ) -> Activities:
		log.debug( f'fetching {self.name} activities from {src_fs}' )
		imported_activities = Activities()
		classifier = self._cfg.get( CFG_CLASSIFIER ) or self.name

		session_files = sorted( [ f for f in src_fs.walk.files( '/', filter=[ TRAINING_SESSION_GLOB ] ) ] )
		log.debug( f'found {len( session_files )} activity files in {src_fs}' )

		if not self.ctx.force:
			log.debug( f'checking db for already existing activities ...' )

			for af, ex in zip_longest( session_files, existing := [] ):
				# old version, not valid any longer from 2026-03 onwards
				if m := RX_TRAINING_SESSION_V1.fullmatch( af ):
					_uid = uid_( f'{classifier}:{m.groupdict().get( "nid")}' )

				# new version, old exercises before 2026-03
				elif m := RX_TRAINING_SESSION_V2A.fullmatch( af ):
					_uid = uid_( f'{classifier}:{m.groupdict().get( "nid")}' )

				# new version, new exercises after 2026-03
				elif m := RX_TRAINING_SESSION_V2B.fullmatch( af ):
					# this is more complicated: we cannot derive the id from the filename :-(
					_uid = None

				if not self.db.contains_activity( _uid ):
					existing.append( af )

			session_files = existing

			log.debug( f'found {len( session_files)} activities which do not yet exist in db' )

		for file in session_files:
			# session may contain multiple activities
			session = self._session_importer.load_as_activity( fs=src_fs, path=file, attach=False )

			for a in session:
				for r in a.resources:
					# update resources paths and unload
					r.path = self.db_path_for( a.uid.local_id, r.path ) # path to update resource
					r.source = self.src_path_for( src_fs, file )
					r.unload_to( dest_fs, r.path )

				imported_activities.append( a )

		return imported_activities

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
			sysexit( -1 )#

		data = {
			'csrfToken': token,
			'email': self.cfg_value( 'username' ),
			'password': self.cfg_value( 'password' ),
			'returnUrl': '/'
		}

		# noinspection PyUnusedLocal
		response = self._session.post( self.login_url, headers=HEADERS_LOGIN, data=data )

		self._logged_in = True

		return self._logged_in

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		if kwargs.get( 'from_takeouts', False ):
			return self.take_importer.fetch( fs=self.ctx.takeout_fs( self.name ), existing_uids=kwargs.get( 'existing_uids' ), force=force )

		else:
			try:
				url = self.events_url_for( range_from=kwargs.get( 'range_from' ), range_to=kwargs.get( 'range_to' ) )
				json_list = self.json_handler.load( url=url, headers=HEADERS_API, session=self._session, stream=False )

				return [
					self.importer.save_to_resource(
						content=self.json_handler.save_raw( j ),
						raw=j,
						data=self.importer.load_data( j ),
						uid=f'{self.name}:{ _local_id( j ) }',
						path=f'{_local_id( j )}.json',
						type=POLAR_FLOW_TYPE,
						source=self.url_for_id( _local_id( j ) ),
					) for j in json_list.raw
				]

			except RuntimeError:
				log.error( f'error fetching activity ids' )
				return []

	def download( self, summary: Resource, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		try:
			if not summary.raw:
				load_resource( summary, update_raw=True )
			multipart = _is_multipart_id( summary.raw.get( 'iconUrl' ) )
		except AttributeError:
			multipart = False

		self.login()

		return self.download_multipart_resources( summary ) if multipart else self.download_resources( summary )

	def download_multipart_resources( self, summary: Resource ) -> List[Resource]:
		resources = [
			Resource( uid=summary.uid, type=POLAR_ZIP_GPX_TYPE, path=f'{summary.local_id}.gpx.zip', source=f'{self.export_url}/gpx/{summary.local_id}?compress=true' ),
			Resource( uid=summary.uid, type=POLAR_ZIP_TCX_TYPE, path=f'{summary.local_id}.tcx.zip', source=f'{self.export_url}/tcx/{summary.local_id}?compress=true' ),
		]

		for r in list( resources ):
			try:
				self.download_resource( r )
				resources.extend( decompress_resources( r, self.gpx_importer ) )
			except (CreateFailed, BadZipFile):
				log.debug( f'error fetching resource from {r.source}', exc_info=True )

			if not r.content:
				resources.remove( r )

		return resources

	def download_resources( self, summary: Resource ) -> List[Resource]:
		resources = [
			Resource(
				uid=summary.uid,
				type=POLAR_CSV_TYPE,
				path=f'{summary.local_id}.csv',
				source=f'{self.export_url}/csv/{summary.local_id}'
			),
			Resource(
				uid=summary.uid,
				type=GPX_TYPE,
				path=f'{summary.local_id}.gpx',
				source=f'{self.export_url}/gpx/{summary.local_id}'
			),
			Resource(
				uid=summary.uid,
				type=TCX_TYPE,
				path=f'{summary.local_id}.tcx',
				source=f'{self.export_url}/tcx/{summary.local_id}'
			),
			Resource(
				uid=summary.uid,
				type=POLAR_HRV_TYPE,
				path=f'{summary.local_id}.hrv.csv',
				source=f'{self.export_url}/rr/csv/{summary.local_id}'
			)
		]

		for r in list( resources ):
			try:
				self.download_resource( r )
			except RuntimeError:
				log.error( f'error fetching resource from {r.source}', exc_info=True )

			if not r.content:
				resources.remove( r )

		return resources

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		log.debug( f'downloading resource from {resource.source}' )
		response = self._session.get( resource.source, headers=HEADERS_DOWNLOAD, allow_redirects=True, stream=False )
		resource.content = response.content
		resource.status = response.status_code
		return response.content, response.status_code

	def postprocess_activities( self, activities: List[Activity], resources: List[Resource], **kwargs ) -> List[Activity]:
		if not any( r.type in [POLAR_ZIP_GPX_TYPE, POLAR_ZIP_TCX_TYPE] for r in resources ):
			return activities

		summary = next( (r for r in resources if r.summary), None )
		recordings = [r for r in resources if r.type in [GPX_TYPE, TCX_TYPE]]
		activity = activities[0] # there should be only one activity
		partlist = self.create_partlist( activity, recordings )

		# create separate activity for each part
		for rp in partlist:
			# try to create activity from tcx
			try:
				tcx_resource = next( (tcx for tcx in rp.resources if tcx.type == TCX_TYPE), None )
				new_activity = Service.as_activity_from( tcx_resource )
			except AttributeError:
				try:
					gpx_resource = next( (gpx for gpx in rp.resources if gpx.type == GPX_TYPE), None )
					new_activity = Service.as_activity_from( gpx_resource )
				except AttributeError:
					new_activity = None

			if new_activity:
				# update new activity
				new_activity.starttime=rp.range.start_datetime
				new_activity.starttime_local = rp.range.start_datetime.astimezone( tzlocal() )
				new_activity.endtime=rp.range.end_datetime
				new_activity.endtime_local = rp.range.end_datetime.astimezone( tzlocal() )
				new_activity.uid=f'{summary.uid}#{rp.index}'
				# self.ctx.db.insert_activity( new_activity )
				activities.append( new_activity )
			else:
				log.error( f'unable to find TCX or GPX resources for multipart activity {summary.uid}, please report, this should not happen' )

		# update main activity with parts
		# self.ctx.db.set_field( Query().uids == [activity.uid], 'parts', activity.parts )
		# self.ctx.db.upsert_activity( activity )
		return activities

	# noinspection PyMethodMayBeStatic
	def unzip_resources( self, resources: List[Resource] ) -> List[Resource]:
		unzipped_resources = []
		for r in list( resources ):
			if r.type in [POLAR_ZIP_GPX_TYPE, POLAR_ZIP_TCX_TYPE]:
				unzipped_resources.extend( decompress_resources( r, self.gpx_importer ) )
		return unzipped_resources

	# noinspection PyMethodMayBeStatic
	def create_partlist( self, activity: Activity, resources: List[Resource] ) -> List[ResourcePartlist]:
		ranges: Dict[int, ResourcePartlist] = { }
		for r in resources:
			recording = Service.as_activity_from( r )
			dtr = DateTimeRange( recording.starttime, recording.endtime )

			found_key = None
			for k, v in ranges.items():
				if dtr.is_intersection( v.range ):
					found_key = k
					break

			if found_key is None:
				ranges[len( ranges.keys() )] = ResourcePartlist( resources=[r], range=dtr )
			else:
				ranges.get( found_key ).range.encompass( dtr )
				ranges.get( found_key ).resources.append( r )

		# sort and number parts
		partlists = sorted( ranges.values(), key=lambda pl: pl.start() )

		for index in range( len( partlists ) ):
			partlists[index].index = index + 1
			if index == 0:
				gap = '00:00:00'
			else:
				gap = seconds_to_time( (partlists[index].start() - partlists[index - 1].end()).total_seconds() ).isoformat()
			uids = [f'{activity.uids[0]}?{r.path}' for r in partlists[index].resources]
			activity.parts.append( ActivityPart( gap=time.fromisoformat( gap ), uids=uids ) )

		return partlists

INTRO = f'For Polar Flow we will use their inofficial Web API to download activity data, that\'s why your credentials are needed.'

@setup
def setup( ctx: ApplicationContext, config: Dict, state: Dict ) -> Tuple[Dict, Dict]:
	ctx.console.print( INTRO, width=120 )

	user = Prompt.ask( 'Enter your user name', console=ctx.console, default=config.get( 'username', '' ) )
	password = Prompt.ask( 'Enter your password', console=ctx.console, default=config.get( 'password' ), password=True )

	return { 'username': user, 'password': password }, {}

# --- helper

def _local_id( r: Mapping ) -> int:
	return _raw_id( r )

def _raw_id( r: Mapping ) -> int:
	r = r or { }
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
	return ICON_TYPES.get( id, Types.unknown )

def _is_multipart_id( icon_url: str ) -> bool:
	return True if icon_url and (icon_url.endswith( ICON_ID_TRIATHLON ) or icon_url.endswith( ICON_ID_MULTISPORT )) else False

def _multipart_str( self ) -> str:
	if self.multipart:
		return '\u2705'
	else:
		return '\u2716'

def decompress_resources( r: Resource, gpx_importer: GPXImporter ) -> List[Resource]:
	mem_fs = open_fs( 'mem://' )
	mem_fs.writebytes( f'/{r.path}', r.content )
	resources = []

	with mem_fs.openbin( f'/{r.path}' ) as zip_file:
		with ReadZipFS( zip_file ) as zip_fs:
			for f in zip_fs.listdir( '/' ):
				resource = Resource( path=f, content=zip_fs.readbytes( f'/{f}' ), status=200, uid=r.uid, source=r.path )
				resource.type = GPX_TYPE if f.endswith( '.gpx' ) else TCX_TYPE
				gpx_importer.load_as_activity( resource=resource )
				resources.append( resource )

	return resources

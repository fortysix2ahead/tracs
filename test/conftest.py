
from importlib.resources import path as resource_path
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List
from typing import Optional
from typing import Tuple

from bottle import Bottle
from fs.base import FS
from fs.memoryfs import MemoryFS
from fs.mountfs import MountFS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from pytest import fixture
from yaml import load as load_yaml
from yaml import SafeLoader

from tracs.config import ApplicationConfig as cfg
from tracs.config import ApplicationConfig as state
from tracs.config import ApplicationContext
from tracs.config import KEY_PLUGINS
from tracs.db import ActivityDb
from tracs.plugins.bikecitizens import Bikecitizens
from tracs.plugins.polar import Polar
from tracs.registry import Registry
from tracs.service import Service
from .bikecitizens_server import bikecitizens_server
from .bikecitizens_server import bikecitizens_server_thread
from .helpers import cleanup as cleanup_path
from .helpers import get_db
from .helpers import get_db_as_json
from .helpers import get_file_as_json
from .helpers import get_file_path
from .helpers import prepare_context
from .helpers import var_run_path
from .polar_server import LIVE_BASE_URL as POLAR_LIVE_BASE_URL
from .polar_server import polar_server
from .polar_server import polar_server_thread
from .polar_server import TEST_BASE_URL as POLAR_TEST_BASE_URL
from .strava_server import strava_server
from .strava_server import strava_server_thread

log = getLogger( __name__ )

ENABLE_LIVE_TESTS = 'ENABLE_LIVE_TESTS'
PERSISTANCE_NAME = 'persistance_layer'

def marker( request, name, key, default ):
	try:
		return request.node.get_closest_marker( name ).kwargs.get( key )
	except (AttributeError, TypeError):
		log.error( f'unable to access marker {name}.{key}', exc_info=True )
		return default

# shared fixtures

@fixture
def db( request ) -> ActivityDb:
	if marker := request.node.get_closest_marker( 'db' ):
		template = marker.kwargs.get( 'template' )
		library_template = marker.kwargs.get( 'library' )
		read_only = marker.kwargs.get( 'read_only', True )
		cleanup = marker.kwargs.get( 'cleanup', True )
	else:
		return None

	db = get_db( template=template, read_only=read_only )

	# set base path in services
	if library_template:
		for name, instance in Registry.services.items():
			# noinspection PyPropertyAccess
			instance.base_path = Path( db.path, name )

	yield db

	if cleanup and not read_only:
		cleanup_path( db.path )

@fixture
def config( request ) -> None:
	if marker := request.node.get_closest_marker( 'config' ):
		template = marker.kwargs.get( 'template' )
		writable = marker.kwargs.get( 'writable', False )
		cleanup = marker.kwargs.get( 'cleanup', True )
	else:
		return None

@fixture
def ctx( request ) -> Optional[ApplicationContext]:
	try:
		marker = request.node.get_closest_marker( 'context' )

		if marker:
			config = marker.kwargs.get( 'config' )
			lib = marker.kwargs.get( 'library' )
			takeout = marker.kwargs.get( 'takeout' )
			do_cleanup = marker.kwargs.get( 'cleanup' )

			context: ApplicationContext = prepare_context( config, lib, takeout )
		else:
			do_cleanup = True
			context: ApplicationContext = ApplicationContext( config_dir=str( var_run_path() ), verbose=True )

		yield context

		if context.db is not None:
			context.db.close()

		if do_cleanup:
			cleanup_path( Path( context.config_dir ) )

	except ValueError:
		log.error( 'unable to run fixture context', exc_info=True )

@fixture
def registry( request ) -> Registry:
	yield Registry.instance()

@fixture
def fs( request ) -> FS:
	cfg_name = marker( request, 'context', 'config', None )
	lib_name = marker( request, 'context', 'lib', None )
	overlay_name = marker( request, 'context', 'overlay', None )
	takeout_name = marker( request, 'context', 'takeout', None )
	var_name = marker( request, 'context', 'var', None )
	persist = marker( request, 'context', 'persist', False )
	cleanup = marker( request, 'context', 'cleanup', True )

	root_fs = MultiFS()
	mount_fs = MountFS()

	if persist == 'disk':
		vrp = var_run_path().absolute()
		root_fs.add_fs( PERSISTANCE_NAME, OSFS( str( vrp ) ), write=True )
		log.info( f'created new temporary persistance dir in {str( vrp )}' )

	elif persist == 'mem':
		root_fs.add_fs( PERSISTANCE_NAME, MemoryFS(), write=True )

	root_fs.add_fs( 'mount', mount_fs )

	with resource_path( 'test', '__init__.py' ) as rp:
		tp = str( rp.parent.resolve().absolute() )
		if cfg_name:
			root_fs.add_fs( 'cfg', OSFS( f'{tp}/configurations/{cfg_name}' ) )

		if lib_name:
			mount_fs.mount( '/db', OSFS( f'{tp}/libraries/{lib_name}' ) )

		if overlay_name:
			mount_fs.mount( '/overlay', OSFS( f'{tp}/overlays/{overlay_name}' ) )

		if takeout_name:
			mount_fs.mount( '/takeouts', OSFS( f'{tp}/takeouts/{takeout_name}' ) )

		if var_name:
			mount_fs.mount( '/var', OSFS( f'{tp}/var/{var_name}' ) )

	yield root_fs

	if cleanup:
		if (pl := root_fs.get_fs( PERSISTANCE_NAME )) and isinstance( pl, OSFS ):
			syspath = pl.getsyspath( '/' )
			cleanup_path( Path( syspath ) )
			log.info( f'cleaned up temporary persistance dir {syspath}' )

@fixture
def json( request ) -> Optional[Dict]:
	if marker := request.node.get_closest_marker( 'db' ):
		template = marker.kwargs.get( 'template', 'empty' )
		return get_db_as_json( template )
	elif marker := request.node.get_closest_marker( 'file' ):
		return get_file_as_json( marker.args[0] )

@fixture
def path( request ) -> Optional[Path]:
	if marker := request.node.get_closest_marker( 'file' ):
		return get_file_path( marker.args[0] )

@fixture
def config_state( request ) -> Optional[Tuple[Dict, Dict]]:
	config_dict, state_dict = None, None

	if config_marker := request.node.get_closest_marker( 'config_file' ):
		with path( 'test', '__init__.py' ) as test_pkg_path:
			config_path = Path( test_pkg_path.parent.parent, 'var', config_marker.args[0] )
			if config_path.exists():
				cfg.set_file( config_path )
				config_dict = load_yaml( config_path.read_bytes(), SafeLoader )

	if state_marker := request.node.get_closest_marker( 'state_file' ):
		with path( 'test', '__init__.py' ) as test_pkg_path:
			state_path = Path( test_pkg_path.parent.parent, 'var', state_marker.args[0] )
			if state_path.exists():
				state.set_file( state_path )
				state_dict = load_yaml( state_path.read_bytes(), SafeLoader )

	return config_dict, state_dict

@fixture
def service( request, ctx ) -> Optional[Service]:
	try:
		marker = request.node.get_closest_marker( 'service' )
		service_class = marker.kwargs.get( 'cls' )
		service_class_name = service_class.__name__.lower()
		base_path = Path( ctx.db_dir, service_class_name )

		Registry.instance()._services[service_class_name] = service_class( ctx=ctx, **{ 'base_path': base_path, **marker.kwargs} )
		return Registry.instance().services[service_class_name]

	except ValueError:
		log.error( 'unable to run fixture service', exc_info=True )

# bikecitizens specific fixtures

@fixture
def bikecitizens_server() -> Bottle:
	if not bikecitizens_server_thread.is_alive():
		bikecitizens_server_thread.start()
	return bikecitizens_server

@fixture
def bikecitizens_service( request ) -> Optional[Bikecitizens]:
	if marker := request.node.get_closest_marker( 'base_url' ):
		service = Bikecitizens()
		service.base_url = marker.args[0]
		return service
	return None

# polar specific fixtures

@fixture
def polar_server() -> Bottle:
	if not polar_server_thread.is_alive():
		polar_server_thread.start()
	return polar_server

@fixture
def polar_service( request ) -> Optional[Polar]:
	if marker := request.node.get_closest_marker( 'base_url' ):
		service = Polar()
		service.base_url = marker.args[0]
		return service
	return None

@fixture
def polar_test_service() -> Polar:
	polar = Polar()
	polar.base_url = POLAR_TEST_BASE_URL

	cfg[KEY_PLUGINS]['polar']['username'] = 'sample user'
	cfg[KEY_PLUGINS]['polar']['password'] = 'sample password'

	return polar

@fixture
def polar_live_service() -> Polar:
	polar = Polar()
	polar.base_url = POLAR_LIVE_BASE_URL
	return polar

# strava specific fixtures

@fixture
def strava_server() -> Bottle:
	if not strava_server_thread.is_alive():
		strava_server_thread.start()
	return strava_server

@fixture
def keywords() -> List[str]:
	# load keywords plugin
	from tracs.plugins.rule_extensions import TIME_FRAMES
	return list( Registry.instance().virtual_fields.keys() )

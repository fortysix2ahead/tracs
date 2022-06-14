
from importlib.resources import path
from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Tuple

from bottle import Bottle
from confuse import Configuration
from pytest import fixture
from yaml import SafeLoader
from yaml import load as load_yaml

from tracs.config import ApplicationConfig as cfg
from tracs.config import ApplicationConfig as state
from tracs.config import KEY_PLUGINS
from tracs.db import ActivityDb
from tracs.plugins.bikecitizens import Bikecitizens
from tracs.plugins.polar import Polar
from tracs.plugins.strava import Strava
from tracs.plugins.waze import Waze
from tracs.service import Service

from .bikecitizens_server import bikecitizens_server
from .bikecitizens_server import bikecitizens_server_thread
from .helpers import get_file_db
from .helpers import get_immemory_db
from .helpers import var_run_path
from .polar_server import polar_server
from .polar_server import polar_server_thread
from .polar_server import TEST_BASE_URL as POLAR_TEST_BASE_URL
from .polar_server import LIVE_BASE_URL as POLAR_LIVE_BASE_URL
from .strava_server import strava_server
from .strava_server import strava_server_thread

ENABLE_LIVE_TESTS = 'ENABLE_LIVE_TESTS'

# shared fixtures

@fixture
def db( request ) -> ActivityDb:
	writable = marker.args[0] if (marker := request.node.get_closest_marker( 'db_writable' )) else False
	name = marker.args[0] if (marker := request.node.get_closest_marker('db_name')) else 'db.json'
	inmemory = marker.args[0] if (marker := request.node.get_closest_marker( 'db_inmemory' )) else False
	template = marker.args[0] if (marker := request.node.get_closest_marker( 'db_template' )) else None

	if inmemory:
		return get_immemory_db( db_template=template )
	else:
		return get_file_db( db_template=template )

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
def service( request ) -> Service:
	service_class, base_url = marker.args[0] if (marker := request.node.get_closest_marker( 'service' )) else (None, None)
	config_file = marker.args[0] if (marker := request.node.get_closest_marker( 'config_file' )) else None
	state_file = marker.args[0] if (marker := request.node.get_closest_marker( 'state_file' )) else None

	config, state = None, None
	with path('test', '__init__.py') as test_pkg_path:
		config_path = Path(test_pkg_path.parent.parent, 'var', config_file )
		if config_path.exists():
			config = Configuration( 'test.strava', __name__, read=False )
			config.set_file(config_path)

		state_path = Path(test_pkg_path.parent.parent, 'var', state_file )
		if state_path.exists():
			state = Configuration( 'test.strava', __name__, read=False )
			state.set_file(state_path)

	# noinspection PyCallingNonCallable
	return service_class( base_url=base_url, config=config, state=state )

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

from typing import Optional

from pytest import fixture
from bottle import Bottle

from test.strava_server import server
from test.strava_server import server_thread
from tracs.config import ApplicationConfig as cfg
from tracs.config import KEY_PLUGINS
from tracs.plugins.polar import Polar
from tracs.plugins.strava import Strava

from .polar_server import TEST_BASE_URL as POLAR_TEST_BASE_URL
from .polar_server import LIVE_BASE_URL as POLAR_LIVE_BASE_URL

# shared fixtures

# polar specific fixtures

@fixture
def polar_server() -> Bottle:
	if not server_thread.is_alive():
		server_thread.start()
	return server

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
	if not server_thread.is_alive():
		server_thread.start()
	return server

@fixture
def strava_service( request ) -> Optional[Strava]:
	if marker := request.node.get_closest_marker( 'base_url' ):
		service = Strava()
		service.base_url = marker.args[0]
		return service
	return None

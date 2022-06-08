
from tracs.config import ApplicationConfig as cfg
from tracs.config import KEY_PLUGINS
from tracs.plugins.polar import Polar

from .polar_server import polar_server

LIVE_BASE_URL = 'https://flow.polar.com'
TEST_BASE_URL = 'http://localhost:40080'

def test_constructor():
	polar = Polar()

	assert polar.base_url == f'{LIVE_BASE_URL}'
	assert polar.login_url == f'{LIVE_BASE_URL}/login'
	assert polar.login_ajax_url.startswith( f'{LIVE_BASE_URL}/ajaxLogin?_=' )
	assert polar.events_url == f'{LIVE_BASE_URL}/training/getCalendarEvents'
	assert polar.export_url == f'{LIVE_BASE_URL}/api/export/training'

	polar.base_url = TEST_BASE_URL

	assert polar.base_url == f'{TEST_BASE_URL}'
	assert polar.login_url == f'{TEST_BASE_URL}/login'
	assert polar.login_ajax_url.startswith( f'{TEST_BASE_URL}/ajaxLogin?_=' )
	assert polar.events_url == f'{TEST_BASE_URL}/training/getCalendarEvents'
	assert polar.export_url == f'{TEST_BASE_URL}/api/export/training'

def test_login( polar_server ):
	# create service
	polar = Polar()
	polar.base_url = TEST_BASE_URL

	# configure credentials
	cfg[KEY_PLUGINS]['polar']['username'] = 'sample user'
	cfg[KEY_PLUGINS]['polar']['password'] = 'sample password'

	polar.login()
	assert polar.logged_in

def test_fetch( polar_server ):
	polar = Polar()
	polar.base_url = TEST_BASE_URL
	polar.login()

	fetched = polar._fetch( 2020 )
	assert len( list( fetched ) ) == 1

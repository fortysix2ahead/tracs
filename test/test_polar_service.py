from typing import List

from tracs.activity import Activity
from tracs.config import ApplicationConfig as cfg
from tracs.config import GlobalConfig as gc
from tracs.config import KEY_PLUGINS
from tracs.plugins.polar import Polar, PolarActivity

from .polar_server import polar_server

from .fixtures import db_empty_inmemory

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

def test_service( polar_server ):
	# login
	polar = _service()
	polar.login()

	assert polar.logged_in

	# fetch
	fetched: List[Activity] = list( polar._fetch( 2020 ) )

	assert len( fetched ) == 1
	a = fetched[0]
	assert type( a ) is PolarActivity
	assert a.raw is not None
	assert a.raw_id == 300003
	assert a.raw_name == '300003.json'

	assert len( a.resources ) == 4

	# download
	for r in a.resources:
		content, status = polar._download_file( a, r )
		assert content is not None and status == 200

def test_workflow( polar_server, db_empty_inmemory ):
	gc.db, json = db_empty_inmemory
	polar = _service()

	polar.login()

	fetched = polar.fetch( True )

	assert len( fetched ) == 1

def _service() -> Polar:
	polar = Polar()
	polar.base_url = TEST_BASE_URL
	cfg[KEY_PLUGINS]['polar']['username'] = 'sample user'
	cfg[KEY_PLUGINS]['polar']['password'] = 'sample password'
	return polar

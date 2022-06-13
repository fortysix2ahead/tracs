from os import getenv
from typing import List

from pytest import mark
from pytest import skip

from tracs.activity import Activity
from tracs.config import GlobalConfig as gc
from tracs.plugins.polar import Polar, PolarActivity
from .conftest import ENABLE_LIVE_TESTS

from .fixtures import db_empty_inmemory
from .fixtures import var_dir
from .polar_server import TEST_BASE_URL

LIVE_BASE_URL = 'https://flow.polar.com'

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

def test_service( polar_server, polar_test_service ):
	# login
	polar_test_service.login()
	assert polar_test_service.logged_in

	# fetch
	fetched: List[Activity] = list( polar_test_service._fetch( 2020 ) )

	assert len( fetched ) == 3
	a = fetched[0]
	assert type( a ) is PolarActivity
	assert a.raw is not None
	assert a.raw_id == 300003
	assert a.raw_name == '300003.json'

	assert len( a.resources ) == 4

	# download
	for r in a.resources:
		content, status = polar_test_service._download_file( a, r )
		assert content is not None and status == 200

def test_workflow( polar_server, polar_test_service, db_empty_inmemory, var_dir ):
	gc.db, json = db_empty_inmemory
	gc.db_dir = var_dir
	polar_test_service.login()
	fetched = polar_test_service.fetch( True )

	assert len( fetched ) == 3

@mark.skipif( not getenv( ENABLE_LIVE_TESTS ), reason='live test not enabled' )
@mark.config_file( 'config_live.yaml' )
@mark.db_writable( True )
def test_live_workflow( polar_live_service, db, config_state ):
	cfg, state = config_state
	if not cfg:
		skip( 'configuration for live testing is missing, consider creating $PROJECT/var/config_live.yaml' )

	gc.db = db
	gc.db_dir = db.db_path.parent
	gc.db_file = db.db_path

	polar_live_service.login()
	assert polar_live_service.logged_in

	fetched = polar_live_service.fetch( False )
	assert len( fetched ) > 0

	limit = 1 # don't download everything
	for i in range( limit ):
		polar_live_service.download( fetched[i], force=True, pretend=False )

from os import getenv
from typing import List

from pytest import mark

from tracs.activity import Resource
from tracs.config import GlobalConfig as gc
from tracs.plugins.polar import BASE_URL
from tracs.plugins.polar import Polar
from .conftest import ENABLE_LIVE_TESTS

from .polar_server import TEST_BASE_URL

def test_constructor():
	polar = Polar()

	assert polar.base_url == f'{BASE_URL}'
	assert polar._login_url == f'{BASE_URL}/login'
	assert polar._ajax_login_url.startswith( f'{BASE_URL}/ajaxLogin?_=' )
	assert polar._events_url == f'{BASE_URL}/training/getCalendarEvents'
	assert polar._export_url == f'{BASE_URL}/api/export/training'

	polar = Polar( base_url = TEST_BASE_URL )

	assert polar.base_url == f'{TEST_BASE_URL}'
	assert polar._login_url == f'{TEST_BASE_URL}/login'
	assert polar._ajax_login_url.startswith( f'{TEST_BASE_URL}/ajaxLogin?_=' )
	assert polar._events_url == f'{TEST_BASE_URL}/training/getCalendarEvents'
	assert polar._export_url == f'{TEST_BASE_URL}/api/export/training'

@mark.service( cls=Polar, base_url=TEST_BASE_URL, config='test/configurations/default/config.yaml', state='test/configurations/default/state.yaml' )
def test_service( polar_server, service ):
	# login
	service.login()
	assert service.logged_in

	# fetch
	fetched: List[Resource] = list( service.fetch( False, False ) )

	assert len( fetched ) == 3
	r = fetched[0]
	assert type( r ) is Resource
	assert r.raw is not None
	assert r.status == 200
	assert r.uid == 'polar:300003'

@mark.service( cls=Polar, base_url=TEST_BASE_URL, config='test/configurations/default/config.yaml', state='test/configurations/default/state.yaml' )
@mark.db( template='empty', inmemory=True, update_gc=True )
def test_workflow( polar_server, service, db ):
	service.login()
	fetched = service.fetch( True, False )
	assert len( fetched ) == 3

@mark.skipif( not getenv( ENABLE_LIVE_TESTS ), reason='live test not enabled' )
@mark.service( cls=Polar, url=BASE_URL, config='var/config_live.yaml', state='var/state_live.yaml' )
@mark.db( template='empty', inmemory=True, update_gc=True )
@mark.db_inmemory( True )
def test_live_workflow( service, db, config_state ):
	gc.db = db
	gc.db_dir = db.path.parent
	gc.db_file = db.path

	service.login()
	assert service.logged_in

	fetched = service.fetch( False )
	assert len( fetched ) > 0

	limit = 1 # don't download everything
	for i in range( limit ):
		service.download( fetched[i], force=True, pretend=False )

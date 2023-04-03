
from typing import List
from pytest import mark

from tracs.resources import Resource
from tracs.plugins.polar import BASE_URL
from tracs.plugins.polar import Polar
from .helpers import skip_live

from .polar_server import TEST_BASE_URL

# noinspection PyUnresolvedReferences
@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Polar )
def test_constructor( service ):
	assert service.base_url == f'{BASE_URL}'
	assert service.login_url == f'{BASE_URL}/login'
	assert service.ajax_login_url.startswith( f'{BASE_URL}/ajaxLogin?_=' )
	assert service.events_url == f'{BASE_URL}/training/getCalendarEvents'
	assert service.export_url == f'{BASE_URL}/api/export/training'

# noinspection PyUnresolvedReferences
@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Polar, base_url=TEST_BASE_URL )
def test_constructor_test( service ):
	assert service.base_url == f'{TEST_BASE_URL}'
	assert service.login_url == f'{TEST_BASE_URL}/login'
	assert service.ajax_login_url.startswith( f'{TEST_BASE_URL}/ajaxLogin?_=' )
	assert service.events_url == f'{TEST_BASE_URL}/training/getCalendarEvents'
	assert service.export_url == f'{TEST_BASE_URL}/api/export/training'

@mark.context( library='empty', config='default', cleanup=True )
@mark.service( cls=Polar, base_url=TEST_BASE_URL )
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

@mark.context( library='empty', config='default', cleanup=True )
@mark.service( cls=Polar, base_url=TEST_BASE_URL )
def test_workflow( polar_server, service ):
	service.login()
	fetched = service.fetch( True, False )
	assert len( fetched ) == 3

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
@mark.service( cls=Polar )
def test_live_workflow( service ):
	service.login()
	assert service.logged_in

	fetched = service.fetch( force=False, pretend=False )
	assert len( fetched ) > 0


from datetime import datetime
from typing import List

from pytest import mark

from tracs.resources import Resource
from tracs.plugins.strava import Strava
from tracs.plugins.strava import StravaActivity
from .helpers import skip_live

from .strava_server import TEST_BASE_URL
from .strava_server import LIVE_BASE_URL

# noinspection PyUnresolvedReferences
@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Strava )
def test_constructor( service ):
	assert service.base_url == f'{LIVE_BASE_URL}'
	assert service.login_url == f'{LIVE_BASE_URL}/login'
	assert service.session_url == f'{LIVE_BASE_URL}/session'
	assert service.activities_url == f'{LIVE_BASE_URL}/activities'
	assert service.auth_url == f'{LIVE_BASE_URL}/oauth/authorize'
	assert service.token_url == f'{LIVE_BASE_URL}/oauth/token'

# noinspection PyUnresolvedReferences
@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Strava, base_url=TEST_BASE_URL )
def test_constructor_test( service ):
	assert service.base_url == f'{TEST_BASE_URL}'
	assert service.login_url == f'{TEST_BASE_URL}/login'
	assert service.session_url == f'{TEST_BASE_URL}/session'
	assert service.activities_url == f'{TEST_BASE_URL}/activities'
	assert service.auth_url == f'{TEST_BASE_URL}/oauth/authorize'
	assert service.token_url == f'{TEST_BASE_URL}/oauth/token'

@mark.skip( reason='Mock server for Strava is of no use when using stravalib for communication' )
@mark.context( library='empty', config='default', cleanup=True )
@mark.service( cls=Strava, url=TEST_BASE_URL )
def test_service( strava_server, service: Strava ):
	from tracs.config import ApplicationConfig
	from tracs.config import ApplicationState
	setup_config_state( ApplicationConfig, ApplicationState )

	# login
	# strava_service.login() # login does not work yet, as oauth requires https
	service.weblogin()
	# assert strava_service.logged_in

	# fetch
	fetched: List[Resource] = list( service.fetch( False, False ) )

	assert len( fetched ) == 3
	a = fetched[0]
	assert type( a ) is StravaActivity
	assert a.raw is not None
	assert a.local_id == 300003

	assert len( a.resources ) == 4

	# download
	for r in a.resources:
		content, status = service._download_resource( a, r )
		assert content is not None and status == 200

@mark.skip( reason='Mock server for Strava is of no use when using stravalib for communication' )
@mark.context( library='empty', config='default', cleanup=True )
@mark.service( cls=Strava, url=TEST_BASE_URL )
def test_workflow( strava_server, service ):
	service.login()
	fetched = service.fetch( False, False )

	assert len( fetched ) == 3

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
@mark.service( cls=Strava )
def test_live_workflow( service ):
	service.login()
	assert service.logged_in

	fetched = service.fetch( False, False )
	assert len( fetched ) > 0

# helper

def setup_config_state( cfg, state ):
	# manually set username/password/access token
	cfg['plugins']['strava']['username'] = 'sample user'
	cfg['plugins']['strava']['password'] = 'sample password'
	cfg['plugins']['strava']['client_id'] = '00000000'
	cfg['plugins']['strava']['client_secret'] = '00000000'
	state['plugins']['strava']['access_token'] = '00000000'
	state['plugins']['strava']['refresh_token'] = '00000000'
	state['plugins']['strava']['token_type'] = '00000000'
	state['plugins']['strava']['expires_at'] = datetime.utcnow().timestamp() + 3600
	state['plugins']['strava']['expires_in'] = 3600

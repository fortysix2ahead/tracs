from datetime import datetime
from os import getenv
from typing import List

from pytest import mark

from tracs.activity import Activity
from tracs.config import GlobalConfig as gc
from tracs.plugins.strava import Strava
from tracs.plugins.strava import StravaActivity
from .conftest import ENABLE_LIVE_TESTS

from .strava_server import TEST_BASE_URL
from .strava_server import LIVE_BASE_URL

def test_constructor():
	strava = Strava()

	assert strava._base_url == f'{LIVE_BASE_URL}'
	assert strava._login_url == f'{LIVE_BASE_URL}/login'
	assert strava._session_url == f'{LIVE_BASE_URL}/session'
	assert strava._activities_url == f'{LIVE_BASE_URL}/activities'
	assert strava._auth_url == f'{LIVE_BASE_URL}/oauth/authorize'
	assert strava._token_url == f'{LIVE_BASE_URL}/oauth/token'

	strava.base_url = TEST_BASE_URL

	assert strava._base_url == f'{TEST_BASE_URL}'
	assert strava._login_url == f'{TEST_BASE_URL}/login'
	assert strava._session_url == f'{TEST_BASE_URL}/session'
	assert strava._activities_url == f'{TEST_BASE_URL}/activities'
	assert strava._auth_url == f'{TEST_BASE_URL}/oauth/authorize'
	assert strava._token_url == f'{TEST_BASE_URL}/oauth/token'

	strava = Strava( base_url = TEST_BASE_URL )

	assert strava._base_url == f'{TEST_BASE_URL}'
	assert strava._login_url == f'{TEST_BASE_URL}/login'
	assert strava._session_url == f'{TEST_BASE_URL}/session'
	assert strava._activities_url == f'{TEST_BASE_URL}/activities'
	assert strava._auth_url == f'{TEST_BASE_URL}/oauth/authorize'
	assert strava._token_url == f'{TEST_BASE_URL}/oauth/token'

@mark.service( (Strava, TEST_BASE_URL) )
@mark.service_config( ('test/configurations/default/config.yaml', 'test/configurations/default/state_test.yaml' ) )
def test_service( strava_server, service ):
	from tracs.config import ApplicationConfig
	from tracs.config import ApplicationState
	setup_config_state( ApplicationConfig, ApplicationState )

	# login
	# strava_service.login() # login does not work yet, as oauth requires https
	service.weblogin()
	# assert strava_service.logged_in

	# fetch
	fetched: List[Activity] = list( service._fetch() )

	assert len( fetched ) == 3
	a = fetched[0]
	assert type( a ) is StravaActivity
	assert a.raw is not None
	assert a.raw_id == 300003
	assert a.raw_name == '300003.json'

	assert len( a.resources ) == 4

	# download
	for r in a.resources:
		content, status = service._download_file( a, r )
		assert content is not None and status == 200

@mark.service( (Strava, TEST_BASE_URL) )
@mark.service_config( ('test/configurations/default/config.yaml', 'test/configurations/default/state_test.yaml' ) )
def test_workflow( strava_server, service, db_empty_inmemory, var_dir ):
	gc.db, json = db_empty_inmemory
	gc.db_dir = var_dir
	service.login()
	fetched = service.fetch( True )

	assert len( fetched ) == 3

@mark.skipif( not getenv( ENABLE_LIVE_TESTS ), reason='live test not enabled' )
@mark.service( (Strava, LIVE_BASE_URL) )
@mark.service_config( ('var/config_live.yaml', 'var/state_live.yaml' ) )
@mark.db_inmemory( True )
def test_live_workflow( service, db, config_state ):
	gc.db = db
	gc.db_dir = db.path.parent
	gc.db_file = db.path

	service.login()
	assert service.logged_in

	fetched = service.fetch( False )
	assert len( fetched ) > 0

	limit = 1  # don't download everything
	for i in range( limit ):
		service.download( fetched[i], force=True, pretend=False )

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

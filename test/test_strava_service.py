from datetime import datetime
from typing import List

from pytest import mark
from pytest import skip

from tracs.activity import Activity
from tracs.config import GlobalConfig as gc
from tracs.plugins.strava import Strava
from tracs.plugins.strava import StravaActivity

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

@mark.base_url( TEST_BASE_URL )
def test_service( strava_server, strava_service ):
	from tracs.config import ApplicationConfig
	from tracs.config import ApplicationState
	setup_config_state( ApplicationConfig, ApplicationState )

	# login
	# strava_service.login() # login does not work yet, as oauth requires https
	strava_service.weblogin()
	# assert strava_service.logged_in

	# fetch
	fetched: List[Activity] = list( strava_service._fetch( 2020 ) )

	assert len( fetched ) == 3
	a = fetched[0]
	assert type( a ) is StravaActivity
	assert a.raw is not None
	assert a.raw_id == 300003
	assert a.raw_name == '300003.json'

	assert len( a.resources ) == 4

	# download
	for r in a.resources:
		content, status = strava_service._download_file( a, r )
		assert content is not None and status == 200

def test_workflow( strava_server, strava_service, db_empty_inmemory, var_dir ):
	gc.db, json = db_empty_inmemory
	gc.db_dir = var_dir
	strava_service.login()
	fetched = strava_service.fetch( True )

	assert len( fetched ) == 3

@mark.service( (Strava, LIVE_BASE_URL) )
@mark.config_file( 'config_live.yaml' )
@mark.state_file( 'state_live.yaml' )
@mark.db_writable( True )
def test_live_workflow( service, db, config_state ):
	cfg, state = config_state
	if not cfg:
		skip( 'configuration for live testing is missing, consider creating $PROJECT/var/config_live.yaml' )

	gc.db = db
	gc.db_dir = db.db_path.parent
	gc.db_file = db.db_path

	service.login()
	assert service.logged_in

	fetched = service.fetch( False )
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

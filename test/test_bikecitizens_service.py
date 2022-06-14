
from os import getenv

from pytest import mark
from pytest import skip

from tracs.config import GlobalConfig as gc
from tracs.plugins.bikecitizens import Bikecitizens
from tracs.plugins.bikecitizens import BASE_URL
from tracs.plugins.bikecitizens import API_URL

from .conftest import ENABLE_LIVE_TESTS
from .fixtures import var_config
from .bikecitizens_server import TEST_API_URL
from .bikecitizens_server import TEST_BASE_URL

def test_live() -> bool:
	return True

def test_constructor():
	bikecitizens = Bikecitizens()

	assert bikecitizens.api_url == f'{API_URL}'
	assert bikecitizens.base_url == f'{BASE_URL}'
	assert bikecitizens._signin_url == f'{BASE_URL}/users/sign_in'
	assert bikecitizens._user_url == f'{API_URL}/api/v1/users/None'

	bikecitizens.api_url = TEST_API_URL
	bikecitizens.base_url = TEST_BASE_URL

	assert bikecitizens.api_url == f'{TEST_API_URL}'
	assert bikecitizens.base_url == f'{TEST_BASE_URL}'
	assert bikecitizens._signin_url == f'{TEST_BASE_URL}/users/sign_in'
	assert bikecitizens._user_url == f'{TEST_BASE_URL}/api/v1/users/None'

@mark.skipif( not getenv( ENABLE_LIVE_TESTS ), reason='live test not enabled' )
@mark.service( (Bikecitizens, BASE_URL) )
@mark.config_file( 'config_live.yaml' )
@mark.state_file( 'state_live.yaml' )
@mark.writable( True )
def test_live_workflow( service, db, config_state ):
	cfg, state = config_state
	if not cfg:
		skip( 'configuration for live testing is missing, consider creating $PROJECT/var/config_live.yaml' )

	gc.db = db
	gc.db_dir = db.db_path.parent
	gc.db_file = db.db_path

	service.login()
	#assert service.logged_in

	fetched = service.fetch( False )
	assert len( fetched ) > 0

	limit = 1 # don't download everything
	for i in range( limit ):
		service.download( fetched[i], force=True, pretend=False )
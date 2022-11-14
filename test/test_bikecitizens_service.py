
from pytest import mark

import tracs.registry
from tracs.plugin.bikecitizens import Bikecitizens
from tracs.plugin.bikecitizens import BASE_URL
from tracs.plugin.bikecitizens import API_URL

from .bikecitizens_server import TEST_API_URL
from .bikecitizens_server import TEST_BASE_URL
from .helpers import skip_live

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

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
@tracs.registry.service( cls=Bikecitizens, url=BASE_URL )
def test_live_workflow( service ):
	service.login()
	assert service.logged_in

	fetched = list( service.fetch( False, False ) )
	assert len( fetched ) == 2

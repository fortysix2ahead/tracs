
from pytest import mark

from tracs.plugins.bikecitizens import Bikecitizens
from tracs.plugins.bikecitizens import BASE_URL
from tracs.plugins.bikecitizens import API_URL
from tracs.service import Service

from .bikecitizens_server import TEST_API_URL
from .bikecitizens_server import TEST_BASE_URL
from .helpers import skip_live

@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Bikecitizens, url=TEST_BASE_URL, api_url=TEST_API_URL )
def test_testservice_creation( service: Bikecitizens ):
	assert type( service ) is Bikecitizens

	assert service.api_url == f'{TEST_API_URL}'
	assert service.base_url == f'{TEST_BASE_URL}'
	assert service.signin_url == f'{TEST_BASE_URL}/users/sign_in'
	assert service.user_url == f'{TEST_BASE_URL}/api/v1/users/None'

@mark.context( library='empty', config='live', cleanup=False )
@mark.service( cls=Bikecitizens, url=BASE_URL )
def test_service_creation( service: Bikecitizens ):
	assert type( service ) is Bikecitizens

	assert service.api_url == f'{API_URL}'
	assert service.base_url == f'{BASE_URL}'
	assert service.signin_url == f'{BASE_URL}/users/sign_in'
	assert service.user_url == f'{API_URL}/api/v1/users/None'

	assert service.base_url == BASE_URL
	assert service.base_path is not None and service.overlay_path is not None

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
@mark.service( cls=Bikecitizens, url=BASE_URL )
def test_live_workflow( service: Service ):
	assert service.login()

	fetched = list( service.fetch( False, False ) )
	assert len( fetched ) == 2


from pytest import mark

from tracs.plugins.bikecitizens import Bikecitizens
from tracs.plugins.bikecitizens import BASE_URL
from tracs.plugins.bikecitizens import API_URL
from tracs.service import Service

from .helpers import skip_live

@mark.context( env='live', persist='clone', cleanup=True )
@mark.service( cls=Bikecitizens )
def test_service_creation( service: Bikecitizens ):
	assert type( service ) is Bikecitizens

	assert service.api_url == f'{API_URL}'
	assert service.base_url == f'{BASE_URL}'
	assert service.signin_url == f'{BASE_URL}/users/sign_in'
	assert service.user_url == f'{API_URL}/api/v1/users/None'

	assert service.base_url == BASE_URL
	# assert service.base_path is not None and service.overlay_path is not None

@skip_live
@mark.context( env='live', persist='clone', cleanup=False )
@mark.service( cls=Bikecitizens, init=True, register=True )
def test_workflow( service: Service ):
	assert service.login()

	fetched = list( service.fetch( False, False ) )
	assert len( fetched ) == 2

	downloaded = []
	for r in fetched:
		downloaded.extend( service.download( r ) )
	assert len( downloaded ) == 4

	service.persist_resources( downloaded, force=False, pretend=False )

	fs = service.ctx.lib_fs
	paths = list( fs.walk.files( 'db/bikecitizens' ) )
	assert any( p.endswith( '8201735.gpx' ) for p in paths )

	# re-download should result in no results
	downloaded = []
	for r in fetched:
		downloaded.extend( service.download( r ) )
	assert len( downloaded ) == 0

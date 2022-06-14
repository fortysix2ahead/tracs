
from pytest import mark

from tracs.db_storage import OrJSONStorage

from .helpers import get_db_path

@mark.db_template( 'default' )
def test_read( json ):
	storage = OrJSONStorage( path=None, use_memory_storage=False )
	assert storage.memory_storage.memory is None

	storage = OrJSONStorage( path=None, use_memory_storage=True )
	assert storage.memory_storage.memory == {}

	path = get_db_path( 'default', False )
	storage = OrJSONStorage( path=path, use_memory_storage=False )
	assert storage.memory_storage.memory is None
	data = storage.read()
	assert data is not None and len( data.keys() ) == 2 and len( data['activities'] ) > 0

	storage = OrJSONStorage( path=path, use_memory_storage=True )
	assert storage.memory_storage.memory is not None
	data = storage.memory_storage.memory
	assert data is not None and len( data.keys() ) == 2 and len( data['activities'] ) > 0

@mark.db_template( 'default' )
def test_write( json ):
	path = get_db_path( 'empty', True )
	storage = OrJSONStorage( path=path, use_memory_storage=True )
	storage.write( json )

	assert storage.memory_storage.memory is not None
	data = storage.memory_storage.memory
	assert data is not None and len( data.keys() ) == 2 and len( data['activities'] ) > 0

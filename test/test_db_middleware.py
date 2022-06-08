
from datetime import datetime

from dateutil.tz import UTC
from dateutil.tz import tzlocal

from tinydb import TinyDB
from tinydb.operations import set
from tinydb.storages import MemoryStorage

from tracs.activity_types import ActivityTypes
from tracs.db import DB_VERSION
from tracs.db_storage import OrJSONStorage

from .helpers import get_db_path

table_data = {
	'_default': {
		'1': {
			'version': 10
		}
	},
	'activities': {
		'1': {
			'_classifier': 'polar',
			'_raw': {
				'type': 'Hiking',
			},
			'name': 'name',
			'type': 'hike',
			'__test_field': 'field name should never be created, just for testing',
		},
		'2': {
			'_classifier': 'polar',
			'_raw': {
				'type': 'Hiking',
			},
		},
		'3': {
			'_classifier': 'polar',
			'_raw': {},
			'type': 'hike',
		}
	}
}

def test_read_data():

	storage_cls = MemoryStorage
	storage_cls = ClassMapMiddleware( storage_cls, { 'activities': ClassifiedDocument } )
	db = TinyDB( storage=storage_cls )

	# db setup, populate memory
	ccm = db.storage
	ms = ccm.storage
	ms.memory = table_data

	d = ccm.read().get( 'activities' ).get( '1' )
	assert type( d ) == ClassifiedDocument

	d = ccm.read().get( '_default' ).get( '1' )
	assert type( d ) == dict

def test_json_memory_storage():
	db_path = get_db_path( 'default' )
	db = TinyDB( path=db_path, storage=JSONMemoryStorage )

	assert db.table( '_default' ) is not None
	assert db.table( 'activities' ) is not None

	d = db.table( '_default' ).get( doc_id=1 )
	assert d['version'] == DB_VERSION

	db.table( '_default' ).update( set( 'version', 100 ), doc_ids=[1] )
	d = db.table( '_default' ).get( doc_id=1 )
	assert d['version'] == 100

def test_orjson_storage():
	db_path = get_db_path( 'default' )

	db = TinyDB( path=db_path, storage=OrJSONStorage )
	assert db.table( '_default' ) is not None
	assert db.table( 'activities' ) is not None
	assert len( db.table( '_default' ).all() ) > 0
	assert len( db.table( 'activities' ).all() ) > 0

	db = TinyDB( path=db_path, storage=OrJSONStorage, use_memory_store=True )
	assert db.table( '_default' ) is not None
	assert db.table( 'activities' ) is not None
	assert len( db.table( '_default' ).all() ) > 0
	assert len( db.table( 'activities' ).all() ) > 0

	db = TinyDB( path=None, storage=OrJSONStorage, use_memory_store=True )
	assert db.table( '_default' ) is not None
	assert db.table( 'activities' ) is not None
	assert len( db.table( '_default' ).all() ) == 0
	assert len( db.table( 'activities' ).all() ) == 0

	cls_map = { 'activities': ClassifiedDocument }
	db = TinyDB( path=db_path, storage=OrJSONStorage, use_memory_store=True, cls_map=cls_map )
	db.table( 'activities' ).document_class = ClassifiedDocument

	assert type( db.storage ) == OrJSONStorage
	# noinspection PyUnresolvedReferences
	d = db.storage.memory_storage.memory.get( 'activities' ).get( '1' )
	assert type( d ) == ClassifiedDocument

def test_orjson_write():
	db_path = get_db_path( 'empty', True )
	cls_map = { 'activities': ClassifiedDocument }
	db = TinyDB( path=db_path, storage=OrJSONStorage, cls_map=cls_map )

	doc = {
		'date': datetime.utcnow().date(),
		'datetime': datetime.utcnow(),
		'utctime': datetime( 2020, 1, 2, 3, 4, 5, tzinfo=UTC ),
		'localtime': datetime( 2020, 1, 2, 3, 4, 5, tzinfo=tzlocal() ),
		'time': datetime.utcnow().time(),
		'type': ActivityTypes.run,
	}

	db.insert( doc )
	db.close()


from typing import cast

from tinydb import JSONStorage
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from tracs.db_middleware import DataClassMiddleware
from tracs.db import document_cls
from tracs.db import document_factory
from tracs.plugins.polar import PolarActivity

from .helpers import get_db_path

def test_read_data( json_default_db ):
	storage_cls = DataClassMiddleware( MemoryStorage )
	db = TinyDB( storage=storage_cls )

	# db setup, populate memory
	mw = cast( DataClassMiddleware, db.storage )
	ms = cast( MemoryStorage, mw.storage )
	ms.memory = json_default_db

	# setup transmap
	mw.transmap['activities'] = document_cls

	# try read operations
	data = mw.read()

	assert 'activities' in data
	assert '2' in data['activities']
	assert type( data['activities']['2'] ) is PolarActivity

def test_read_data_from_disk():
	storage_cls = DataClassMiddleware( JSONStorage )
	db = TinyDB( path=get_db_path( 'default' ), storage=storage_cls )
	db.table( 'activities' ).document_class = document_factory

	assert type( db.table( 'activities' ).get( doc_id = 2 ) ) is PolarActivity

def test_write_data( json_default_db ):
	polar_raw = json_default_db['activities']['2']['_raw']
	polar = PolarActivity( raw=polar_raw )

	# set up db
	db = TinyDB( storage=DataClassMiddleware( MemoryStorage ) )
	mw = cast( DataClassMiddleware, db.storage )
	mw.transmap['activities'] = document_cls
	ms = cast( MemoryStorage, mw.storage )

	db.table( 'activities' ).insert( polar )

	assert ms.memory['activities']['1'] == {
		'calories': 2904,
		'_classifier': 'polar',
		'distance': 30000.1,
		'duration': '03:23:53',
		'localtime': '2012-01-07T10:40:51+01:00',
		'_metadata': {},
		'name': '03:23:53;0.0 km',
		'raw_id': 1234567890,
		'_resources': [],
		'tags': [],
		'time': '2012-01-07T09:40:51+00:00',
		'type': 'xcski_classic'
	}
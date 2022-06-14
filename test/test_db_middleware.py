
from typing import cast

from pytest import mark
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from tracs.db import document_cls
from tracs.db_middleware import DataClassMiddleware
from tracs.plugins.polar import PolarActivity

@mark.db_template( 'default' )
def test_read_data( json ):
	storage_cls = DataClassMiddleware( MemoryStorage )
	db = TinyDB( storage=storage_cls )

	# db setup, populate memory
	mw = cast( DataClassMiddleware, db.storage )
	ms = cast( MemoryStorage, mw.storage )
	ms.memory = json

	# setup transmap
	mw.transmap['activities'] = document_cls

	# try read operations
	data = mw.read()

	assert 'activities' in data
	assert '2' in data['activities']
	assert type( data['activities']['2'] ) is PolarActivity

def test_read_data_from_disk():
	pass

@mark.db_template( 'default' )
def test_write_data( db, json ):
	polar_raw = json['activities']['2']['_raw']
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

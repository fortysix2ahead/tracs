
from datetime import datetime
from datetime import time
from typing import cast

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from pytest import mark
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from tracs.activity import Resource
from tracs.activity_types import ActivityTypes
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

def test_write():
	resource = Resource( name='one', type='gpx', status=100, path='one.gpx' )
	polar = PolarActivity(
		doc_id = 1,
		calories = 2904,
		distance = 30000.1,
		duration = time( 3, 23, 53 ),
		localtime = datetime( 2012, 1, 7, 10, 40, 51, tzinfo=tzlocal() ),
		name = '03:23:53;0.0 km',
		raw_id = 1234567890,
		resources = [resource],
		time = datetime( 2012, 1, 7, 9, 40, 51, tzinfo=UTC ),
		type = ActivityTypes.xcski_classic,
	)
	storage = DataClassMiddleware( storage_cls=MemoryStorage )()
	storage.transmap['activities'] = document_cls
	memory_storage = cast( MemoryStorage, storage.storage )

	data = {
		"activities": {
			"1": polar
		}
	}

	storage.write( data )
	written_data = memory_storage.memory

	assert written_data == { 'activities' :
		{
			'1': {
				'calories': 2904,
				'classifier': 'polar',
				'distance': 30000.1,
				'duration': '03:23:53',
				'groups': {},
				'localtime': '2012-01-07T10:40:51+01:00',
				'metadata': {},
				'name': '03:23:53;0.0 km',
				'raw_id': 1234567890,
				'resources': [
					{
						'name': 'one',
						'path': 'one.gpx',
						'status': 100,
						'type': 'gpx'
					}
				],
				'tags': [],
				'time': '2012-01-07T09:40:51+00:00',
				'type': 'xcski_classic'
			}
		}
	}

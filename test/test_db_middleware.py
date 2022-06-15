from datetime import datetime
from datetime import time
from json import loads as load_json
from pathlib import Path
from typing import cast

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from pytest import mark
from tinydb import JSONStorage
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from test.helpers import var_run_path
from tracs.activity import Resource
from tracs.activity_types import ActivityTypes
from tracs.db import document_cls
from tracs.db_middleware import DataClassMiddleware
from tracs.plugins.polar import PolarActivity


@mark.db_template( 'default' )
def test_read( json ):
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


def test_write():
	data = {
		"activities": {
			"1": PolarActivity(
				doc_id=1,
				calories=2904,
				distance=30000.1,
				duration=time( 3, 23, 53 ),
				localtime=datetime( 2012, 1, 7, 10, 40, 51, tzinfo=tzlocal() ),
				name='03:23:53;0.0 km',
				raw_id=1234567890,
				resources=[Resource( name='one', type='gpx', status=100, path='one.gpx' )],
				time=datetime( 2012, 1, 7, 9, 40, 51, tzinfo=UTC ),
				type=ActivityTypes.xcski_classic,
			)
		}
	}

	serialized_memory_data = {
		'activities':
			{
				'1': {
					'calories'  : 2904,
					'classifier': 'polar',
					'distance'  : 30000.1,
					'duration'  : '03:23:53',
					'groups'    : {},
					'localtime' : '2012-01-07T10:40:51+01:00',
					'metadata'  : {},
					'name'      : '03:23:53;0.0 km',
					'raw_id'    : 1234567890,
					'resources' : [
						{
							'name'  : 'one',
							'path'  : 'one.gpx',
							'status': 100,
							'type'  : 'gpx'
						}
					],
					'tags'      : [],
					'time'      : '2012-01-07T09:40:51+00:00',
					'type'      : 'xcski_classic'
				}
			}
	}

	serialized_file_data = {
		'activities': {
			'1': {
				'classifier': 'polar',
				'groups'    : {},
				'metadata'  : {},
				'resources' : [{
					'name'  : 'one',
					'path'  : 'one.gpx',
					'status': 100,
					'type'  : 'gpx'
				}],
				'calories'  : 2904,
				'distance'  : 30000.1,
				'duration'  : '03:23:53',
				'localtime' : '2012-01-07T10:40:51+01:00',
				'name'      : '03:23:53;0.0 km',
				'raw_id'    : 1234567890,
				'tags'      : [],
				'time'      : '2012-01-07T09:40:51+00:00',
				'type'      : 'xcski_classic'
			}
		}
	}

	storage = DataClassMiddleware( storage_cls=MemoryStorage )()
	storage.transmap['activities'] = document_cls
	memory_storage = cast( MemoryStorage, storage.storage )

	storage.write( data )
	written_data = memory_storage.memory

	assert written_data == serialized_memory_data
	path = Path( var_run_path(), 'db.json' )

	storage = DataClassMiddleware( storage_cls=JSONStorage )( path=path )
	storage.transmap['activities'] = document_cls
	storage.write( data )

	with open( path, 'r' ) as f:
		written_data = load_json( f.read() )
		assert written_data == serialized_file_data

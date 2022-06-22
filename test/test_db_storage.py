
from datetime import datetime
from datetime import time

from dateutil.tz import UTC
from dateutil.tz import tzlocal
from pytest import mark
from orjson import loads as load_json

from tracs.activity import Resource
from tracs.activity_types import ActivityTypes
from tracs.db import document_cls
from tracs.db_storage import DataClassStorage
from tracs.plugins.polar import PolarActivity
from tracs.plugins.strava import StravaActivity
from tracs.plugins.waze import WazeActivity

from .helpers import get_db_path
from .helpers import get_writable_db_path

@mark.db( template='default' )
def test_read( json ):
	storage = DataClassStorage( path=None, use_memory_storage=False )
	assert storage.memory.memory is None

	storage = DataClassStorage( path=None, use_memory_storage=True )
	assert storage.memory.memory is None

	# read from default db template
	path, db_path, meta_path = get_db_path( 'default', False )

	storage = DataClassStorage( path=db_path, use_memory_storage=True )
	assert storage.memory.memory is None
	data = storage.read()
	assert data is not None and len( data.items() ) == 1 and len( data['_default'].items() ) > 0

	# type is dict as transformation_map is still empty
	assert type( data['_default'].get( '2' ) ) is dict

	# setup transformation map
	storage.factory = document_cls
	data = storage.read()
	assert type( data['_default'].get( '2' ) ) is PolarActivity
	assert type( data['_default'].get( '3' ) ) is StravaActivity
	assert type( data['_default'].get( '4' ) ) is WazeActivity

@mark.db( template='default' )
def test_write( json ):
	path, db_path, meta_path = get_db_path( 'empty', False )
	storage = DataClassStorage( path=path, use_memory_storage=True )
	storage.write( json )

	data = storage.memory.memory
	assert data is not None and len( data.items() ) == 1 and len( data['_default'].items() ) > 0

	# test storage with test data

	data = {
		"_default": {
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
		'_default':
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
		'_default': {
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

	# setup transformation map
	storage.factory = document_cls
	storage.write( data )
	written_data = storage.memory.memory
	assert written_data == serialized_memory_data

	path, db_path, meta_path = get_writable_db_path( 'empty' )
	storage = DataClassStorage( path=db_path, use_memory_storage=False, factory=document_cls )
	storage.write( data )

	with open( db_path, 'r' ) as f:
		written_data = load_json( f.read() )
		assert written_data == serialized_file_data

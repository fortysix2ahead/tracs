
from copy import deepcopy
from datetime import datetime
from datetime import time
from pathlib import Path

from dateutil.tz import UTC
from dateutil.tz import tzlocal
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS
from pytest import mark
from orjson import loads as load_json
from orjson import dumps as save_json
from rich import print as pp

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import document_cls
from tracs.db_storage import DataClassStorage
from tracs.db_storage import DataClassStorage2
from tracs.db_storage import OrJSONStorage
from tracs.plugins.polar import PolarActivity
from tracs.resources import Resource

unserialized_data = {
	"_default": {
		"1": Activity(
			doc_id=1,
			calories=2904,
			distance=30000.1,
			duration=time( 3, 23, 53 ),
			localtime=datetime( 2012, 1, 7, 10, 40, 51, tzinfo=tzlocal() ),
			name='03:23:53;0.0 km',
			raw_id=1234567890,
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

@mark.db( template='default' )
def test_read( db ):
	# read without deserializers
	data = OrJSONStorage( path=db.db_path, access_mode='r' ).read()
	assert type( data['_default']['1']['time'] ) is str
	assert type( data['_default']['1']['type'] ) is str

	data = OrJSONStorage( path=db.db_path, access_mode='r', deserializers=DataClassStorage.deserializers ).read()

	assert type( data['_default']['1']['time'] ) is datetime
	assert type( data['_default']['1']['localtime'] ) is datetime
	assert type( data['_default']['1']['type'] ) is ActivityTypes

	# pure memory storage
	storage = DataClassStorage( path=None, use_memory_storage=False )
	assert storage.memory_storage.memory is None

	storage = DataClassStorage( path=None, use_memory_storage=True )
	assert storage.memory_storage.memory is None

	storage = DataClassStorage( path=db.db_path, use_memory_storage=True )
	assert storage.memory_storage.memory is not None
	data = storage.read()
	assert data is not None and len( data.items() ) == 1 and len( data['_default'].items() ) > 0

	storage = DataClassStorage( path=db.db_path, use_memory_storage=True, passthrough=False )
	assert storage.memory_storage.memory is not None
	data = storage.read()
	assert data is not None and len( data.items() ) == 1 and len( data['_default'].items() ) > 0
	assert type( data['_default']['1'] ) is Activity

@mark.db( template='empty', inmemory=False, writable=True )
def test_write( db ):
	storage = OrJSONStorage( path=db.db_path, access_mode='r+' )
	storage.write( serialized_file_data )

	data = storage.read()
	assert type( data['_default']['1'] ) is not None

	storage = DataClassStorage( path=db.db_path, use_memory_storage=True )
	storage.write( deepcopy( unserialized_data ) )
	written_data = storage.memory_storage.memory
	assert written_data == unserialized_data

	storage = DataClassStorage( path=db.db_path, use_memory_storage=False, use_serializers=True )
	storage.write( deepcopy( unserialized_data ) )
	with open( db.db_path, 'r' ) as f:
		written_data = load_json( f.read() )
		assert written_data == serialized_file_data

# todo: this test case needs an update
@mark.db( template='default', inmemory=False, writable=True )
def test_cache( db ):
	# create storage and read
	storage = DataClassStorage( path=db.db_path, use_memory_storage=False, use_cache=False, use_serializers=True )
	data = storage.read()
	assert type( data['_default']['1'] ) is PolarActivity
	assert data['_default']['1']['name'] == 'Some Location'
	assert type( storage.memory.memory['_default']['1'] ) is PolarActivity

	# change activity name on disk
	_set_activity_name( db_path, 'Some Other Location' )

	# read again, new name should be set
	data = storage.read()
	assert data['_default']['1']['name'] == 'Some Other Location'

	# turn on cache
	storage = DataClassStorage( path=db_path, use_memory_storage=False, cache=True, cache_size=1, document_factory=document_cls )
	data = storage.read()
	assert data['_default']['1']['name'] == 'Some Other Location'

	# change name and read again (10 times)
	_set_activity_name( db_path, 'Very Distant Location' )
	for read_cycle in range( 10 ):
		data = storage.read()
		assert data['_default']['1']['name'] == 'Some Other Location'

	# turn off cache, read, change data, write and read again
	storage = DataClassStorage( path=db_path, use_memory_storage=False, cache=False, document_factory=document_cls )
	data = storage.read()
	assert data['_default']['1']['name'] == 'Very Distant Location'
	data['_default']['1']['name'] = 'Very Close Location'
	storage.write( data )
	data = storage.read()
	assert data['_default']['1']['name'] == 'Very Close Location'

	# turn on cache
	storage = DataClassStorage( path=db_path, use_memory_storage=False, cache=True, cache_size=1, document_factory=document_cls )
	data = storage.read()
	assert data['_default']['1']['name'] == 'Very Close Location'

	# change data and write
	data['_default']['1']['name'] = 'Far Location'
	storage.write( data )

	# read (this time from cache)
	assert _get_activity_name( db_path ) == 'Very Close Location'

	# write again (cache hits are cache_size now) and read again
	storage.write( data )
	assert _get_activity_name( db_path ) == 'Far Location'

# todo: this test case needs an update
@mark.db( template='default', inmemory=False, writable=True )
def test_passthrough( db ):
	storage = DataClassStorage( path=None, use_memory_storage=True, use_cache=False, use_serializers=True )
	storage.write( deepcopy( unserialized_data ) )
	assert type( storage.memory_storage.memory['_default']['1'] ) is dict

	# data is None as this read is considered the initial one, this should not happen in live operation (always read before first write)
	data = storage.read()
	storage.write( deepcopy( unserialized_data ) ) # write and read again
	data = storage.read()
	assert type( data['_default']['1'] ) is PolarActivity

	storage = DataClassStorage( path=None, use_memory_storage=True, cache=False, document_factory=document_cls, passthrough=True )
	storage.write( deepcopy( unserialized_data ) )
	assert type( storage.memory.memory['_default']['1'] ) is PolarActivity
	# data is None as this read is considered the initial one, this should not happen in live operation (always read before first write)
	data = storage.read()
	storage.memory.memory = deepcopy( serialized_memory_data )
	data = storage.read()
	assert type( data['_default']['1'] ) is dict

@mark.file( 'databases/empty/schema.json' )
def test_create_storage2( path ):
	storage = DataClassStorage2( path=None, read_only=True, passthrough=False )
	assert storage.mem_as_bytes() == b''
	assert storage.mem_as_str() == ''
	assert storage.mem_as_dict() == {}

	storage = DataClassStorage2( path=path, read_only=True, passthrough=False )
	assert storage.mem_as_str() == '{\n  "_default": {\n    "1": {\n      "version": 12\n    }\n  }\n}\n'
	assert storage.mem_as_dict() == {'_default': {'1': {'version': 12}}}

@mark.file( 'databases/empty/schema.json' )
def test_read2( path ):
	storage = DataClassStorage2( path=None, read_only=True, passthrough=False )
	assert storage.read() == {}

	storage = DataClassStorage2( path=path, read_only=True, passthrough=False )
	assert storage.read() == {'_default': {'1': {'version': 12}}}

@mark.file( 'databases/empty/schema.json' )
def test_write2( path ):
	storage = DataClassStorage2( path=None, read_only=True, passthrough=False )
	storage.write( {'_default': {'1': {'version': 1}}} )
	assert storage.mem_as_dict() == {'_default': {'1': {'version': 1}}}

	dt = datetime( 2020, 1, 1, 9, 10, 11, tzinfo=UTC )
	storage.write( {'datetimes': {'1': dt } } )
	assert storage.mem_as_dict() == {'datetimes': {'1': dt.isoformat() } }

	t = time( 20, 1, 1 )
	storage.write( { 'times': { '1': t } } )
	assert storage.mem_as_dict() == { 'times': { '1': t.isoformat() } }

	r = Resource()
	storage.write( { 'resources': { '1': r } } )

	pp( storage.mem_as_dict() )
	return

	assert storage.mem_as_dict() == { 'resources': { '1': '' } }

	a = Activity()
	storage.write( { 'activities': { '1': a } } )
	assert storage.mem_as_dict() == { 'activities': { '1': '' } }

# helpers

def _get_activity_name( db_path: Path ) -> str:
	with open( db_path, mode='r+', encoding='UTF-8' ) as p:
		json_data = load_json( p.read() )
		return json_data['_default']['1']['name']

def _set_activity_name( db_path: Path, s: str ) -> None:
	with open( db_path, mode='r+', encoding='UTF-8' ) as p:
		json_data = load_json( p.read() )
		p.seek( 0 )
		json_data['_default']['1']['name'] = s
		p.write( save_json( json_data, option=OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS ).decode() )

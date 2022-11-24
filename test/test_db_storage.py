from datetime import datetime
from datetime import time
from pathlib import Path

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from orjson import dumps as save_json
from orjson import loads as load_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS
from pytest import mark

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db_storage import DataClassStorage
from tracs.plugins.gpx import GPX_TYPE
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
			tags=[ 'one', 'two', 'three' ],
			time=datetime( 2012, 1, 7, 9, 40, 51, tzinfo=UTC ),
			type=ActivityTypes.xcski_classic,
		)
	}
}

serialized_data = {
	'_default': {
		'1': {
			'calories'  : 2904,
			'distance'  : 30000.1,
			'duration'  : '03:23:53',
			'localtime' : '2012-01-07T10:40:51+01:00',
			'name'      : '03:23:53;0.0 km',
			'raw_id'    : 1234567890,
			'tags'      : [ 'one', 'two', 'three' ],
			'time'      : '2012-01-07T09:40:51+00:00',
			'timezone'  : 'Europe/Berlin',
			'type'      : 'xcski_classic'
		}
	}
}

@mark.file( 'databases/empty/schema.json' )
def test_create_storage2( path ):
	storage = DataClassStorage( path=None, read_only=True, passthrough=False )
	assert storage.mem_as_bytes() == b''
	assert storage.mem_as_str() == ''
	assert storage.mem_as_dict() == {}

	storage = DataClassStorage( path=path, read_only=True, passthrough=False )
	assert storage.mem_as_str() == '{\n  "_default": {\n    "1": {\n      "version": 12\n    }\n  }\n}\n'
	assert storage.mem_as_dict() == {'_default': {'1': {'version': 12}}}

@mark.file( 'databases/empty/schema.json' )
def test_read2( path ):
	storage = DataClassStorage( path=None, read_only=True, passthrough=False )
	assert storage.read() == {}

	storage = DataClassStorage( path=path, read_only=True, passthrough=False )
	assert storage.read() == {'_default': {'1': {'version': 12}}}

@mark.file( 'databases/storage.json' )
def test_read2_transform( path ):
	storage = DataClassStorage( path=path, read_only=True, passthrough=False )
	assert storage.read() == serialized_data

@mark.file( 'databases/empty/schema.json' )
def test_write2( path ):
	storage = DataClassStorage( path=None, read_only=True )
	storage.write( {'_default': {'1': {'version': 1}}} )
	assert storage.mem_as_dict() == {'_default': {'1': {'version': 1}}}

	dt = datetime( 2020, 1, 1, 9, 10, 11, tzinfo=UTC )
	storage.write( {'datetimes': {'1': dt } } )
	assert storage.mem_as_dict() == {'datetimes': {'1': dt.isoformat() } }

	t = time( 20, 1, 1 )
	storage.write( { 'times': { '1': t } } )
	assert storage.mem_as_dict() == { 'times': { '1': t.isoformat() } }

	r = Resource( path='test.gpx', type=GPX_TYPE )
	storage.write( { 'resources': { '1': r } } )
	assert storage.mem_as_dict() == { 'resources': { '1': {'path': 'test.gpx', 'summary': False, 'type': 'application/xml+gpx'} } }

	a = Activity()
	storage.write( { 'activities': { '1': a } } )
	assert storage.mem_as_dict() == { 'activities': { '1': { 'timezone': 'Europe/Berlin' } } }

	a = unserialized_data['_default']['1']
	storage.write( { '_default': { '1': a } } )
	assert storage.mem_as_dict() == serialized_data

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

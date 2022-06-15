
from datetime import datetime
from typing import cast

from pytest import mark
from tinydb import TinyDB
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import MemoryStorage
from tinydb.table import Document
from tinydb.table import Table

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from tracs.db_middleware import DataClassMiddleware
from tracs.db_storage import OrJSONStorage
from tracs.plugins.groups import ActivityGroup
from tracs.db import create_db
from tracs.db import DB_VERSION
from tracs.db import document_factory

from tracs.plugins.polar import PolarActivity
from tracs.plugins.strava import StravaActivity
from tracs.plugins.waze import WazeActivity

from .fixtures import db_empty_file
from .helpers import ids
from .helpers import get_db_path

# test cases
from .helpers import var_run_path

# noinspection PyUnresolvedReferences
def test_create_db():
	tdb = TinyDB( storage=MemoryStorage )
	db = create_db( tdb )
	assert db is tdb

	# creation without path

	tdb = create_db( path=None )
	assert type( tdb.storage ) is DataClassMiddleware
	assert type( cast( DataClassMiddleware, tdb.storage ).storage ) is MemoryStorage

	# creation with path
	tdb = create_db( path=get_db_path( 'empty', True ), pretend=True, cache=False )
	assert type( tdb.storage ) is DataClassMiddleware
	assert type( tdb.storage.storage ) is OrJSONStorage
	assert tdb.storage.storage.use_memory_storage is True

	# cache is on
	tdb = create_db( path=get_db_path( 'empty', True ), pretend=True, cache=True )
	assert type( tdb.storage ) is CachingMiddleware
	assert type( tdb.storage.storage ) is DataClassMiddleware
	assert type( tdb.storage.storage.storage ) is OrJSONStorage
	assert tdb.storage.storage.storage.use_memory_storage is True

	tdb = create_db( path=get_db_path( 'empty', True ), pretend=False, cache=False )
	assert type( tdb.storage ) is DataClassMiddleware
	assert type( tdb.storage.storage ) is OrJSONStorage
	assert tdb.storage.storage.use_memory_storage is False

	tdb = create_db( path=get_db_path( 'empty', True ), pretend=False, cache=True )
	assert type( tdb.storage ) is CachingMiddleware
	assert type( tdb.storage.storage ) is DataClassMiddleware
	assert type( tdb.storage.storage.storage ) is OrJSONStorage
	assert tdb.storage.storage.storage.use_memory_storage is False

def test_new_db():
	db = ActivityDb( path=None )
	assert type( db.middleware ) is DataClassMiddleware and type( db.storage ) is MemoryStorage

	db = ActivityDb( path=get_db_path( 'empty', True ), pretend=True, cache=True )
	assert type( db.middleware ) is DataClassMiddleware and type( db.storage ) is OrJSONStorage

	db = ActivityDb( path=get_db_path( 'empty', True ), pretend=False, cache=False )
	assert type( db.middleware ) is DataClassMiddleware and type( db.storage ) is OrJSONStorage

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_open_db( db ):
	assert isinstance( db.default, Table )
	assert isinstance( db.activities, Table )

	assert len( db.default.all() ) == 1
	assert db.default.all()[0]['version'] == DB_VERSION

	assert db.default.document_class is Document
	assert db.activities.document_class is document_factory

@mark.db_inmemory( True )
@mark.db_template( 'empty' )
def test_write_middleware( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

	db.insert( a )
	a = db.get( doc_id = 1 )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

@mark.db_inmemory( False )
@mark.db_template( 'empty' )
def test_write_to_file( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	db.insert( a )

	a = db.get( doc_id = 1 )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

@mark.db_inmemory( True )
@mark.db_template( 'empty' )
def test_insert( db ):
	counter = len( db.activities.all() )
	doc_id = db.insert( { '_raw': {'listItemId': 1212} } )
	assert len( db.activities.all() ) == counter + 1
	db.activities.remove( doc_ids=[doc_id] )
	assert len( db.activities.all() ) == counter

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_contains( db ):
	# check activity table
	assert db.contains( 1 ) == True
	assert db.contains( 111 ) == False

	assert db.contains( raw_id=1234567890 ) == True
	assert db.contains( raw_id=9999 ) == False

	assert db.contains( raw_id=1234567890, service_name='polar' ) == True
	assert db.contains( raw_id=9999, service_name='polar' ) == False

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_all( db ):
	# parameters are: include_groups, include_grouped, include_ungrouped
	# all
	result = ids( db.all( True, True, True ) )
	assert result == [1, 2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	# groups only
	result = ids( db.all( True, False, False ) )
	assert result == [1]

	# grouped only
	result = ids( db.all( False, True, False ) )
	assert result == [2, 3, 4]

	# ungrouped only
	result = ids( db.all( False, False, True ) )
	assert result == [11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	# groups and grouped
	result = ids( db.all( True, True, False ) )
	assert result == [1, 2, 3, 4]

	# groups and ungrouped -> the default case!
	result = ids( db.all( True, False, True ) )
	assert result == [1, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]
	result = ids( db.all() )
	assert result == [1, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	# grouped and ungrouped
	result = ids( db.all( False, True, True ) )
	assert result == [2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	# nothing at all
	result = ids( db.all( False, False, False ) )
	assert result == []

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_get( db ):
	# existing activity -> 1 is considered the doc_id
	a = db.get( 1 )
	assert a.id == 1 and isinstance( a, ActivityGroup )
	a = db.get( 11 )
	assert a.id == 11 and isinstance( a, PolarActivity )

	# get via doc_id
	a = db.get( doc_id=1 )
	assert a.doc_id == 1 and isinstance( a, ActivityGroup )

	# non-existing id
	assert db.get( doc_id=999 ) is None
	assert db.get( raw_id=999 ) is None

	# existing polar activity
	a = db.get( raw_id=1234567890 )
	assert a.id == 2 and isinstance( a, PolarActivity )
	a = db.get( raw_id=1234567890, service_name='polar' )
	assert a.doc_id == 2 and isinstance( a, PolarActivity )

	# non-existing polar activity
	assert db.get( raw_id=999, service_name='polar' ) is None
	assert db.get( doc_id=999, service_name='polar' ) is None

	# existing strava activity
	a = db.get( raw_id=12345678, service_name='strava' )
	assert a.doc_id == 3 and isinstance( a, StravaActivity )

	# existing waze activity
	a = db.get( raw_id=20210101010101, service_name='waze' )
	assert a.doc_id == 4 and isinstance( a, WazeActivity )

	# get with id=0
	assert db.get( 0 ) is None
	assert db.get( doc_id=0 ) is None
	assert db.get( 0, service_name='polar' ) is None
	assert db.get( doc_id=0, service_name='polar' ) is None

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_update( db ):
	a = db.get( 1 )
	assert a.name == 'Unknown Location'
	assert a.type == ActivityTypes.xcski
	assert a['groups']['ids'] == [2, 3, 4]
	assert a['groups']['uids'] == [ 'polar:1234567890', 'strava:12345678', 'waze:20210101010101' ]
	assert a['metadata'] == {}

	a.name = 'Known Location'
	a['additional_field'] = 'additional field value'
	a['groups']['ids'] = [20, 30, 40]

	del( a['type'] )
	# del ( a['_groups']['uids'] ) # this break __post_init__
	del ( a['metadata'] )
	db.update( a )

	# manipulate 'a' to check that objects are decoupled
	a.name = 'Somewhere else'

	a2 = db.get( 1 )
	assert a2.name == 'Known Location'
	assert a2.type is None
	assert a2['additional_field'] is None
	assert a2['groups']['ids'] == [20, 30, 40]
	# assert a2['_groups'].get( 'uids' ) is None
	assert a2['metadata'] == {}

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_remove( db ):
	a = db.get( 30 )
	assert a is not None

	db.remove( a )
	assert db.get( 30 ) is None

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_find_last( db ):
	assert db.find_last( None ).doc_id == 30
	assert db.find_last( 'polar' ).doc_id == 41

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_find( db ):
	# id
	assert db.find_ids( '1' ) == [1]
	assert db.find_ids( '2' ) == [] # exists, but is grouped activity
	assert db.find_ids( 'id:1' ) == [1]
	assert db.find_ids( 'id:2' ) == [] # exists, but is grouped activity
	assert db.find_ids( 'id:20' ) == [20]
	assert db.find_ids( 'id:9999' ) == []

	assert db.find_ids( 'raw_id:1001' ) == [11]

	# name
	assert db.find_ids( 'name:location' ) == [1]
	assert db.find_ids( 'name:location', include_grouped=True ) == [1, 4]

	# service
	assert db.find_ids( 'service:polar' ) == [1, 11, 12, 13, 14, 41, 51, 52]
	assert db.find_ids( 'service:polar', include_grouped=True ) == [1, 2, 11, 12, 13, 14, 41, 51, 52]
	assert db.find_ids( 'service:polar', include_groups=False, include_grouped=False, include_ungrouped=True ) == [11, 12, 13, 14, 41, 51, 52]

	assert db.find_ids( 'service:strava' ) == [1, 20, 40, 53, 54, 55]
	assert db.find_ids( 'service:strava', include_grouped=True ) == [1, 3, 20, 40, 53, 54, 55]

	assert db.find_ids( '^service:polar' ) == [20, 30, 40, 53, 54, 55]
	assert db.find_ids( '^service:polar', include_grouped=True ) == [3, 4, 20, 30, 40, 53, 54, 55]

	assert db.find_ids( '^service:strava' ) == [11, 12, 13, 14, 30, 41, 51, 52]

	# type
	assert db.find_ids( 'type:run' ) == [11]
	assert db.find_ids( '^type:run' ) == [1, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_find_multiple_filters( db ):
	assert ids( db.find( ['service:polar', 'name:afternoon'] ) ) == [11]
	assert ids( db.find( ['service:polar', 'name:location', 'type:xcski'] ) ) == [1]
	# test special case involving id
	assert ids( db.find( ['service:polar', 'id:1', 'name:location', 'type:xcski'] ) ) == [1]

@mark.db_inmemory( True )
@mark.db_template( 'default' )
def test_find_by_id( db ):
	a = db.find_by_id( 2 )
	assert isinstance( a, PolarActivity )
	assert a.doc_id == 2
	assert a.name == '03:23:53;0.0 km'

	a = db.find_by_id( 1001 )
	assert isinstance( a, Activity )
	assert a.name == '00:25:34;0.0 km'

	assert db.find_by_id( 999 ) is None

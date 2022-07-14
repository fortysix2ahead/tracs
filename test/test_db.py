
from datetime import datetime

from pytest import mark
from tinydb.table import Document
from tinydb.table import Table

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from tracs.db_storage import DataClassStorage
from tracs.plugins.groups import ActivityGroup
from tracs.db import document_factory

from tracs.plugins.polar import PolarActivity
from tracs.plugins.strava import StravaActivity
from tracs.plugins.waze import WazeActivity

from .helpers import ids
from .helpers import get_db_path

def test_new_db():
	db = ActivityDb( path=None )
	assert type( db.storage ) is DataClassStorage
	assert db.storage.use_memory_storage is True

	db = ActivityDb( path=None, pretend=True, cache=False )
	assert db.storage.use_memory_storage is True and db.storage.use_cache is True

	db = ActivityDb( path=None, pretend=False, cache=True )
	assert db.storage.use_memory_storage is True and db.storage.use_cache is True

	db = ActivityDb( path=None, pretend=True, cache=True )
	assert db.storage.use_memory_storage is True and db.storage.use_cache is True

	parent_path, db_path, meta_path = get_db_path( 'empty', writable=False )
	db = ActivityDb( path=parent_path, pretend=True, cache=False )
	assert db.storage.use_memory_storage is True and db.storage.use_cache is True

	parent_path, db_path, meta_path = get_db_path( 'empty', writable=True )
	db = ActivityDb( path=parent_path, pretend=False, cache=True )
	assert db.storage.use_memory_storage is False and db.storage.use_cache is True

@mark.db( template='default', inmemory=True )
def test_open_db( db ):
	assert isinstance( db.activities, Table )

	assert len( db.activities.all() ) > 1
	assert db.activities.all()[0]['version'] > 0

	assert db.activities.document_class is Activity

@mark.db( template='empty', inmemory=True )
def test_write_middleware( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

	db.insert( a )
	a = db.get( doc_id = 1 )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

@mark.db( template='empty', inmemory=False, writable=True )
def test_write_to_file( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	db.insert( a )

	a = db.get( doc_id = 1 )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

@mark.db( template='empty', inmemory=True )
def test_insert( db ):
	number_in_db = len( db.activities.all() )
	a = Activity( raw_id = 1000 )
	doc_id = db.insert( a )
	assert len( db.activities.all() ) == number_in_db + 1
	assert a.doc_id == doc_id

	number_in_db = len( db.activities.all() )
	a1 = Activity( raw_id = 1001 )
	a2 = Activity( raw_id = 1002 )
	doc_ids = db.insert( [a1, a2] )
	assert len( db.activities.all() ) == number_in_db + 2
	assert a1.doc_id == doc_ids[0] and a2.doc_id == doc_ids[1]

@mark.db( template='default', inmemory=True )
def test_contains( db ):
	# check activity table
	assert db.contains( 1 ) == True
	assert db.contains( 111 ) == False

	assert db.contains( raw_id=1234567890 ) == True
	assert db.contains( raw_id=9999 ) == False

	assert db.contains( raw_id=1234567890, service_name='polar' ) == True
	assert db.contains( raw_id=9999, service_name='polar' ) == False

@mark.db( template='default', inmemory=True )
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

@mark.db( template='default', inmemory=True )
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

@mark.db( template='default', inmemory=True )
def test_update( db ):
	a = db.get( 1 )
	assert a.name == 'Unknown Location'
	assert a.type == ActivityTypes.xcski
	assert a['group_ids'] == [2, 3, 4]
	assert a['group_uids'] == [ 'polar:1234567890', 'strava:12345678', 'waze:20210101010101' ]
	assert a['metadata'] == {}

	a.name = 'Known Location'
	a['additional_field'] = 'additional field value'
	a['group_ids'] = [20, 30, 40]

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
	assert a2['group_ids'] == [20, 30, 40]
	# assert a2['_groups'].get( 'uids' ) is None
	assert a2['metadata'] == {}

@mark.db( template='default', inmemory=True )
def test_remove( db ):
	a = db.get( 30 )
	assert a is not None

	db.remove( a )
	assert db.get( 30 ) is None

@mark.db( template='default', inmemory=True )
def test_find_last( db ):
	assert db.find_last( None ).doc_id == 30
	assert db.find_last( 'polar' ).doc_id == 41

@mark.db( template='default', inmemory=True )
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
	assert db.find_ids( 'type:xcski' ) == [11]
	assert db.find_ids( '^type:xcski' ) == [1, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

@mark.db( template='default', inmemory=True )
def test_find_multiple_filters( db ):
	assert ids( db.find( ['service:polar', 'name:afternoon'] ) ) == [11]
	assert ids( db.find( ['service:polar', 'name:location', 'type:xcski'] ) ) == [1]
	# test special case involving id
	assert ids( db.find( ['service:polar', 'id:1', 'name:location', 'type:xcski'] ) ) == [1]

@mark.db( template='default', inmemory=True )
def test_find_by_id( db ):
	a = db.find_by_id( 2 )
	assert isinstance( a, PolarActivity )
	assert a.doc_id == 2
	assert a.name == '03:23:53;0.0 km'

	a = db.find_by_id( 1001 )
	assert isinstance( a, Activity )
	assert a.name == '00:25:34;0.0 km'

	assert db.find_by_id( 999 ) is None

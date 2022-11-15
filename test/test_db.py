
from datetime import datetime

from pytest import mark
from tinydb.table import Table

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from tracs.db_storage import DataClassStorage

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

	db_path = get_db_path( 'empty', writable=False )
	db = ActivityDb( path=db_path.parent, pretend=True, cache=False )
	assert db.storage.use_memory_storage is True and db.storage.use_cache is True

	db_path = get_db_path( 'empty', writable=True )
	db = ActivityDb( path=db_path.parent, pretend=False, cache=True )
	assert db.storage.use_memory_storage is False and db.storage.use_cache is True

@mark.db( template='default', inmemory=True )
def test_open_db( db ):
	assert isinstance( db.activities, Table )

	assert len( db.activities.all() ) > 1
	assert db.schema > 0

	assert db.activities.document_class is Activity

@mark.db( template='empty', inmemory=True )
def test_write_middleware( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

	db.insert( a )
	a = db.get( id = 1 )
	assert type( a['time'] ) is datetime
	assert type( a.get( 'time' ) ) is datetime

@mark.db( template='empty', inmemory=False, writable=True )
def test_write_to_file( db ):
	a = StravaActivity( raw = { 'start_date': datetime.utcnow().isoformat() } )
	db.insert( a )

	a = db.get( id = 1 )
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
	assert db.contains( 1 ) is True
	assert db.contains( 111 ) is False

	assert db.contains( raw_id=1234567890 ) is True
	assert db.contains( raw_id=9999 ) is False

	assert db.contains( raw_id=1234567890, classifier='polar' ) is True
	assert db.contains( raw_id=9999, classifier='polar' ) is False

	assert db.contains( uid='polar:1234567890' ) is True
	assert db.contains( uid='polar:9999' ) is False

@mark.db( template='default', inmemory=True )
def test_get( db ):
	# existing activity -> 1 is considered the doc_id
	a = db.get( 1 )
	assert a.id == 1 and isinstance( a, Activity )
	a = db.get( 4 )
	assert a.id == 4 and isinstance( a, Activity )

	# get via doc_id
	a = db.get( id = 1 )
	assert a.doc_id == 1 and isinstance( a, Activity )

	# non-existing id
	assert db.get( id=999 ) is None
	assert db.get( raw_id=999 ) is None

	# existing polar activity
	a = db.get( raw_id=1234567890 )
	assert a.id == 1 and isinstance( a, Activity )
	a = db.get( raw_id=1234567890, classifier='polar' )
	assert a.doc_id == 1 and isinstance( a, Activity )

	# non-existing polar activity
	assert db.get( raw_id=999, classifier='polar' ) is None
	assert db.get( id=999, classifier='polar' ) is None

	# existing strava activity
	a = db.get( raw_id=12345678, classifier='strava' )
	assert a.doc_id == 1 and isinstance( a, Activity )

	# existing waze activity
	a = db.get( raw_id=20210101010101, classifier='waze' )
	assert a.doc_id == 1 and isinstance( a, Activity )

	# get with id=0
	assert db.get( 0 ) is None
	assert db.get( id = 0 ) is None
	assert db.get( 0, classifier='polar' ) is None
	assert db.get( id = 0, classifier='polar' ) is None

@mark.db( template='default', inmemory=True )
def test_get_by_uid( db ):
	assert ( a := db.get_by_uid( 'polar:1234567890' ) ) is not None and 'polar:1234567890' in a.uids and a.resources == []
	assert ( a := db.get_by_uid( 'polar:1234567890', include_resources=True ) ) is not None and len( a.resources ) > 0

@mark.db( template='default', inmemory=True )
def test_update( db ):
	a = db.get( 1 )
	assert a.name == 'Unknown Location'
	assert a.type == ActivityTypes.xcski
	assert a.uids == [ 'polar:1234567890', 'strava:12345678', 'waze:20210101010101' ]

	a.name = 'Known Location'
	a.type = None

	db.update( a )

	# manipulate 'a' to check that objects are decoupled
	a.name = 'Somewhere else'

	a2 = db.get( 1 )
	assert a2.name == 'Known Location'
	# assert a2.type is None # todo: not sure why this fails ...

@mark.db( template='default', inmemory=True )
def test_remove( db ):
	a = db.get( 4 )
	assert a is not None

	db.remove( a )
	assert db.get( 4 ) is None

@mark.db( template='default', inmemory=True )
def test_find_last( db ):
	assert db.find_last( None ).doc_id == 4
	assert db.find_last( 'polar' ).doc_id == 1

@mark.db( template='default', inmemory=True )
def test_find( db ):
	# id
	assert db.find_ids( '1' ) == [1] and db.find_ids( '2' ) == [2]
	assert db.find_ids( 'id:1' ) == [1] and db.find_ids( 'id:2' ) == [2] # exists, but is grouped activity
	assert db.find_ids( 'id:20' ) == []

	assert db.find_ids( 'raw_id:12345678' ) == [3]

	# name
	assert db.find_ids( 'name:location' ) == [1, 4]

	# service
	assert db.find_ids( 'service:polar' ) == [1, 2]
	assert db.find_ids( 'service:strava' ) == [1, 3]
	assert db.find_ids( '^service:polar' ) == [3, 4]
	assert db.find_ids( '^service:strava' ) == [2, 4]

	# type
	assert db.find_ids( 'type:xcski' ) == [1]
	assert db.find_ids( '^type:xcski' ) == [2, 3, 4]

@mark.db( template='default', inmemory=True )
def test_find_multiple_filters( db ):
	assert ids( db.find( ['service:polar', 'name:location'] ) ) == [1]
	assert ids( db.find( ['service:polar', 'name:location', 'type:xcski'] ) ) == [1]
	# test special case involving id
	assert ids( db.find( ['service:polar', 'id:1', 'name:location', 'type:xcski'] ) ) == [1]

@mark.db( template='default', inmemory=True )
def test_find_by_id( db ):
	a = db.find_by_id( 2 )
	assert isinstance( a, Activity ) and a.doc_id == 2 and a.name == '03:23:53;0.0 km'

	a = db.find_by_id( 12345678 )
	assert isinstance( a, Activity ) and a.doc_id == 1 and a.name == 'Unknown Location'

	assert db.find_by_id( 999 ) is None

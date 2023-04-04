
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from pytest import mark

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from .helpers import get_db_path

def test_new_db_without_path():
	db = ActivityDb( path=None )
	assert db.dbfs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.dbfs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 12

	# read_only is ignored in this case
	db = ActivityDb( path=None, read_only=True )
	assert db.dbfs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.dbfs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 12

	# same as above
	db = ActivityDb( path=None, read_only=False )
	assert db.dbfs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.dbfs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 12

def test_new_db_with_path():
	db_path = get_db_path( 'empty', read_only=False )
	db = ActivityDb( path=db_path.parent, read_only=False )
	assert db.dbfs is not None and type( db.underlay_fs ) is OSFS and type( db.overlay_fs ) is MemoryFS
	assert db.dbfs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 12

	db_path = get_db_path( 'empty', read_only=True )
	db = ActivityDb( path=db_path.parent, read_only=True )
	assert db.dbfs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.dbfs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 12

@mark.db( template='default', read_only=True )
def test_open_db( db ):
	assert db.schema.version == 12

	assert len( db.activities ) > 1
	assert db.activities[0] == Activity(
		id=1,
		name='Unknown Location',
		type=ActivityTypes.xcski,
		time=datetime( 2012, 1, 7, 10, 40, 56, tzinfo=timezone.utc ),
		localtime=datetime( 2012, 1, 7, 11, 40, 56, tzinfo=timezone( timedelta( seconds=3600 ) ) ),
		location_place='Forest',
		uids=['polar:1234567890', 'strava:12345678', 'waze:20210101010101'],
	)

@mark.db( template='empty', read_only=True )
def test_insert( db ):
	assert len( db.activities ) == 0
	id = db.insert( Activity() )
	assert len( db.activities ) == 1 and id == 1
	ids = db.insert( Activity(), Activity() )
	assert len( db.activities ) == 3 and ids == [2, 3]
	assert db.activity_keys == [1, 2, 3]

@mark.db( template='default', read_only=True )
def test_contains( db ):
	# check activity table
	assert db.contains_activity( uid='polar:1234567890' ) is True
	assert db.contains_activity( uid='polar:9999' ) is False

@mark.db( template='default', read_only=True )
def test_get( db ):
	assert (a := db.get_by_id( 1 )) and a.id == 1 and isinstance( a, Activity )
	assert (a := db.get_by_id( 4 )) and a.id == 4 and isinstance( a, Activity )

	# non-existing id
	assert db.get_by_id( 999 ) is None

	# existing polar activity
	assert (a := db.get_by_uid( 'polar:1234567890' )) and a.id == 1 and isinstance( a, Activity )

	# non-existing polar activity
	assert db.get_by_uid( 'polar:999' ) is None

	# existing strava activity, same activity as above
	assert (a := db.get_by_uid( 'strava:12345678' )) and a.id == 1 and isinstance( a, Activity )
	assert (a := db.get_by_uid( 'waze:20210101010101' )) and a.id == 1 and isinstance( a, Activity )

	# get with id=0
	assert db.get_by_id( 0 ) is None

@mark.db( template='default', read_only=True )
def test_remove( db ):
	assert ( a := db.get_by_id( 4 ) ) and a is not None
	db.remove_activity( a )
	assert db.get_by_id( 4 ) is None

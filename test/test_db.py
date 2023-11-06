
from datetime import datetime, timedelta, timezone
from typing import List, Union

from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from pytest import mark

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.tcx import TCX_TYPE
from tracs.registry import Registry
from tracs.resources import Resource, ResourceType

def test_new_db_without_path():
	db = ActivityDb( path=None )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

	# read_only is ignored in this case
	db = ActivityDb( path=None, read_only=True )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

	# same as above
	db = ActivityDb( path=None, read_only=False )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

def test_new_db_with_fs():
	db = ActivityDb( fs=MemoryFS() )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

@mark.context( env='empty', persist='clone', cleanup=True )
def test_new_db_with_writable_path( db_path ):
	db = ActivityDb( path=db_path, read_only=False )
	assert db.fs is not None and type( db.underlay_fs ) is OSFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

@mark.context( env='empty', persist='clone', cleanup=True )
def test_new_db_with_readonly_path( db_path ):
	db = ActivityDb( path=db_path, read_only=True )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'index.json', 'metadata.json', 'resources.json', 'schema.json']
	assert db.schema.version == 13

@mark.context( env='default', persist='clone', cleanup=True )
def test_open_db( db ):
	assert db.schema.version == 12

	assert len( db.activities ) > 1
	assert db.activities[0] == Activity(
		id=1,
		name='Unknown Location',
		type=ActivityTypes.xcski,
		starttime=datetime( 2012, 1, 7, 10, 40, 56, tzinfo=timezone.utc ),
		starttime_local=datetime( 2012, 1, 7, 11, 40, 56, tzinfo=timezone( timedelta( seconds=3600 ) ) ),
		location_place='Forest',
		uids=['polar:1234567890', 'strava:12345678', 'waze:20210101010101'],
	)

@mark.context( env='empty', persist='clone', cleanup=True )
def test_insert( db ):
	assert len( db.activities ) == 0
	id = db.insert( Activity() )
	assert len( db.activities ) == 1 and id == [1]
	ids = db.insert( Activity(), Activity() )
	assert len( db.activities ) == 3 and ids == [2, 3]
	assert db.activity_keys == [1, 2, 3]

@mark.context( env='empty', persist='clone', cleanup=True )
def test_insert_resources( db ):
	assert len( db.resources ) == 0

	r1 = Resource( uid='polar:101/recording.gpx' )
	r2 = Resource( uid='polar:102/recording.gpx' )

	assert db.insert_resources( r1, r2 ) == [1, 2]

@mark.context( env='default', persist='clone', cleanup=True )
def test_contains( db ):
	# check activity table
	assert db.contains_activity( uid='polar:1234567890' ) is True
	assert db.contains_activity( uid='polar:9999' ) is False

@mark.context( env='default', persist='clone', cleanup=True )
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

@mark.context( env='parts', persist='clone', cleanup=True )
def test_find_resources( db ):
	assert ids( db.find_resources( 'strava:1001' ) ) == [ 7, 8, 9 ]
	assert ids( db.find_resources( 'strava:1001', '1001.gpx' ) ) == [ 7 ]

	assert ids( db.find_all_resources( ['strava:1001', 'strava:1002' ] ) ) == [ 7, 8, 9, 10, 11, 12 ]

	assert ids( db.find_resources_of_type( GPX_TYPE ) ) == [3, 4, 7, 10]
	assert ids( db.find_resources_of_type( GPX_TYPE, db.find_resources( 'strava:1001' ) ) ) == [7]

	# register strava summary type first, otherwise the test case will fail
	Registry.register_resource_type( ResourceType( type=STRAVA_TYPE, summary=True ) )
	Registry.register_resource_type( ResourceType( type=GPX_TYPE, recording=True ) )
	Registry.register_resource_type( ResourceType( type=TCX_TYPE, recording=True ) )

	assert ids( db.find_summaries( 'strava:1001' ) ) == [ 9 ]
	assert ids( db.find_all_summaries( ['strava:1001'] ) ) == [ 9 ]

	assert ids( db.find_recordings() ) == [3, 4, 5, 6, 7, 8, 10, 11]
	assert ids( db.find_recordings( db.find_resources( 'strava:1001' ) ) ) == [7, 8]

@mark.context( env='parts', persist='clone', cleanup=True )
def test_find_multipart( db ):
	assert ids( db.find_by_classifier( 'strava' ) ) == [ 2, 4, 6 ]
	assert ids( db.find_by_classifier( 'polar' ) ) == [ 1, 3, 5, 6 ]

	# test for strava run 1
	a = db.get_by_id( 2 )
	assert a.uids == ['strava:1001']
	assert ids( db.find_resources_for( a ) ) == [ 7, 8, 9 ]

	# test for the multipart polar activity
	a = db.get_by_id( 1 )
	assert a.uids == ['polar:1001'] and a.multipart
	assert ids( db.find_resources_for( a ) ) == [ 1, 2, 3, 4, 5, 6 ]

	# test for the polar run 1
	a = db.get_by_id( 3 )
	assert all( uid.startswith( 'polar:1001/' ) for uid in a.uids ) and not a.multipart
	assert ids( db.find_resources_for( a ) ) == [ 3, 5 ]

	# test for run 2
	a = db.get_by_id( 6 )
	assert ids( db.find_resources_for( a ) ) == [ 4, 6, 10, 11, 12 ]

@mark.context( env='default', persist='clone', cleanup=True )
def test_remove( db ):
	assert ( a := db.get_by_id( 4 ) ) and a is not None
	db.remove_activity( a )
	assert db.get_by_id( 4 ) is None

# helper

def ids( elements: List[Union[Activity,Resource]] ) -> List[int]:
	return sorted( [e.id for e in elements] )

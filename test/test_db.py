
from datetime import datetime, timedelta, timezone
from typing import List, Union

from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from pytest import mark, raises

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.db import ActivityDb
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.polar import POLAR_FLOW_TYPE
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.tcx import TCX_TYPE
from tracs.resources import Resource

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
	assert db.schema.version == 13

	assert len( db.activities ) > 1
	assert db.activities[0] == Activity(
		id=1,
		name='Unknown Location',
		type=ActivityTypes.xcski,
		starttime=datetime( 2012, 1, 7, 10, 40, 56, tzinfo=timezone.utc ),
		starttime_local=datetime( 2012, 1, 7, 11, 40, 56, tzinfo=timezone( timedelta( seconds=3600 ) ) ),
		location_place='Forest',
		uid='group:1',
		uids=['polar:1234567890', 'strava:12345678', 'waze:20210101010101'],
	)

@mark.context( env='empty', persist='clone', cleanup=True )
def test_insert_upsert_remove( db ):
	assert len( db.activities ) == 0 and len( db.resources ) == 0

	# insert activities and check keys
	id = db.insert( Activity() )
	assert len( db.activities ) == 1 and id == [1]
	ids = db.insert( Activity(), Activity() )
	assert len( db.activities ) == 3 and ids == [2, 3]
	assert db.activity_keys == [1, 2, 3]

	# test insert resources
	r1 = Resource( uid='polar:101/recording.gpx' )
	r2 = Resource( uid='polar:102/recording.gpx' )
	assert db.insert_resources( r1, r2 ) == [1, 2]

	# insert r1 again
	with raises( KeyError ):
		assert db.insert_resources( r1 )

@mark.context( env='default', persist='clone', cleanup=True )
def test_contains( db ):
	assert db.contains_activity( uid='polar:1234567890' ) is True
	assert db.contains_activity( uid='polar:9999' ) is False

	assert db.contains_resource( uid='polar:100001', path='100001.gpx' )
	assert not db.contains_resource( uid='polar:100011', path='100001.gpx' )
	assert not db.contains_resource( uid='polar:100001', path='100001a.gpx' )

@mark.context( env='default', persist='clone', cleanup=True )
def test_get( db ):
	assert (a := db.get_by_id( 1 )) and a.id == 1 and a.uid == 'group:1' and a.name == 'Unknown Location'

	# non-existing id
	assert db.get_by_id( 999 ) is None

	# existing polar activity
	assert db.get_by_uid( 'polar:1234567890' ).id == 2

	# non-existing polar activity
	assert db.get_by_uid( 'polar:999' ) is None

	# existing strava/waze activity
	assert db.get_by_uid( 'strava:12345678' ).id == 3
	assert db.get_by_uid( 'waze:20210101010101' ).id == 4

	# get with id = 0
	assert db.get_by_id( 0 ) is None

	# get by ids/uids
	assert db.get_by_ids( [] ) == []
	assert db.get_by_ids( None ) == []
	assert db.get_by_ids( [ 1, 2, 300 ] ) == [ db.get_by_id( 1 ), db.get_by_id( 2 ) ]
	assert db.get_by_uids( [] ) == []
	assert db.get_by_uids( None ) == []
	assert db.get_by_uids( [ 'group:1' ] ) == [ db.get_by_id( 1 ) ]

	# get by reference
	assert db.get_by_ref( None ) == []
	assert db.get_by_ref( 'polar:1234567890' ) == [ db.get_by_id( 1 ) ]
	assert db.get_by_refs( [] ) == []
	assert db.get_by_refs( None ) == []
	assert db.get_by_refs( [ 'polar:1234567890', 'strava:200001' ] ) == [ db.get_by_id( 1 ), db.get_by_id( 2001 ) ]

	# get resources
	assert db.get_resource_by_id( 1 ).path == '100001.gpx'
	assert db.get_resources_by_uid( 'polar:100001' ) == [ db.get_resource_by_id( 1 ), db.get_resource( 2 ) ]
	lst = [ db.get_resource_by_id( 1 ), db.get_resource( 2 ), db.get_resource_by_id( 3 ), db.get_resource_by_id( 4 ) ]
	assert db.get_resources_by_uids( ['polar:100001', 'strava:200002' ] ) == lst

	assert db.get_resource_by_uid_path( 'polar:100001', '100001.gpx' ) == db.get_resource_by_id( 1 )

@mark.context( env='default', persist='clone', cleanup=True )
@mark.db( summary_types=[POLAR_FLOW_TYPE, STRAVA_TYPE], recording_types=[GPX_TYPE, TCX_TYPE] )
def test_find( db ):
	assert ids( db.find_resources( 'polar:100001' ) ) == [ 1, 2 ]
	assert ids( db.find_resources( 'polar:100001', '100001.json' ) ) == [ 2 ]

	assert ids( db.find_all_resources( ['polar:100001', 'strava:200002' ] ) ) == [ 1, 2, 3, 4 ]

	assert ids( db.find_resources_of_type( GPX_TYPE ) ) == [1, 3]

	assert ids( db.find_summaries( 'polar:100001' ) ) == [ 2 ]
	assert ids( db.find_all_summaries( ['polar:100001', 'strava:200002'] ) ) == [ 2, 4 ]

	assert ids( db.find_recordings( 'polar:100001' ) ) == [ 1 ]
	assert ids( db.find_all_recordings( ['polar:100001', 'strava:200002'] ) ) == [ 1, 3 ]

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

# helper

def ids( elements: List[Union[Activity,Resource]] ) -> List[int]:
	return sorted( [e.id for e in elements] )

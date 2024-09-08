from typing import List, Union

from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from pytest import mark

from objects import DEFAULT_ONE
from tracs.activity import Activity
from tracs.db import ActivityDb
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.polar import POLAR_FLOW_TYPE
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.tcx import TCX_TYPE
from tracs.resources import Resource

def test_new_db_without_path():
	db = ActivityDb( path=None )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

	# read_only is ignored in this case
	db = ActivityDb( path=None, read_only=True )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

	# same as above
	db = ActivityDb( path=None, read_only=False )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

def test_new_db_with_fs():
	db = ActivityDb( fs=MemoryFS() )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

@mark.context( env='empty', persist='clone', cleanup=True )
def test_new_db_with_writable_path( db_path ):
	db = ActivityDb( path=db_path, read_only=False )
	assert db.fs is not None and type( db.underlay_fs ) is OSFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

@mark.context( env='empty', persist='clone', cleanup=True )
def test_new_db_with_readonly_path( db_path ):
	db = ActivityDb( path=db_path, read_only=True )
	assert db.fs is not None and type( db.underlay_fs ) is MemoryFS and type( db.overlay_fs ) is MemoryFS
	assert db.fs.listdir( '/' ) == ['activities.json', 'schema.json']
	assert db.schema.version == 14

@mark.xfail( reason='comparison of activities does not yet work correctly' )
@mark.context( env='default', persist='clone', cleanup=True )
def test_open_db( db ):
	assert db.schema.version == 14

	assert len( db.activities ) > 1
	assert db.activities[0] == DEFAULT_ONE

@mark.context( env='empty', persist='clone', cleanup=True )
def test_insert_upsert_remove( db ):
	assert len( db.activities ) == 0 and len( db.resources ) == 0

	# insert activities and check keys
	id = db.insert( Activity() )
	assert len( db.activities ) == 1 and id == [1]
	ids = db.insert( Activity(), Activity() )
	assert len( db.activities ) == 3 and ids == [2, 3]
	assert db.activity_keys == [1, 2, 3]

	# upsert
	a = Activity( name='one', uid='one:101' )
	id = db.upsert_activity( a )
	assert db.get_by_id( id )
	a = Activity( name='two', uid='one:101', calories=100 )
	id = db.upsert_activity( a )
	a = db.get_by_id( id )
	assert a.name == 'one' and a.uid == 'one:101' and a.calories == 100

@mark.context( env='default', persist='clone', cleanup=True )
def test_contains( db ):
	assert db.contains( 'polar:1001' )
	assert db.contains( 'polar:1005' )
	assert not db.contains( 'polar:999' )

	assert db.contains_activity( uid='polar:1001' )
	assert db.contains_activity( uid='polar:1005' )
	assert not db.contains_activity( uid='polar:999' )

	assert db.contains( uid='polar:1001/1001.gpx' )
	assert db.contains( uid='polar:1005/1005.gpx' )
	assert not db.contains( uid='polar:1001/1001.xxx' )

	assert db.contains_resource( uid='polar:1001', path='polar/1/0/0/1001/1001.gpx' )
	assert db.contains_resource( uid='polar:1001', path='1001.gpx' )
	assert db.contains_resource( uid='polar:1005', path='polar/1/0/0/1005/1005.gpx' )
	assert db.contains_resource( uid='polar:1005', path='1005.gpx' )
	assert not db.contains_resource( uid='polar:1001', path='polar/1/0/0/1001/1001.xxx' )
	assert not db.contains_resource( uid='polar:999', path='999.gpx' )

@mark.context( env='default', persist='clone', cleanup=True )
@mark.db( summary_types=[POLAR_FLOW_TYPE, STRAVA_TYPE], recording_types=[GPX_TYPE, TCX_TYPE] )
def test_get( db ):
	# get activity by id
	a = db.get_by_id( 1 )
	assert a.id == 1 and a.uid == 'group:1001' and a.name == 'Somewhere in the Forest'

	# non-existing id
	assert db.get_by_id( 0 ) is None
	assert db.get_by_id( 999 ) is None

	# existing activity
	assert db.get_by_uid( 'polar:1001' ).id == 2
	assert db.get_by_uid( 'strava:1001' ).id == 3

	# non-existing polar activity
	assert db.get_by_uid( 'polar:999' ) is None

	# get groups by uid
	assert db.get_group_for_uid( None ) is None
	assert db.get_group_for_uid( 'polar:1001' ).id == 1

	# get resources
	assert db.get_resource_by_uid_path( 'polar:1001', 'polar/1/0/0/1001/1001.gpx' ) == db.get_by_id( 2 ).resources[0]

	# get_for resources
	assert [ r.path for r in db.get_resources_for_uid( 'polar:1001' ) ] == ['polar/1/0/0/1001/1001.gpx', 'polar/1/0/0/1001/1001.json']

@mark.context( env='default', persist='clone', cleanup=True )
@mark.db( summary_types=[POLAR_FLOW_TYPE, STRAVA_TYPE], recording_types=[GPX_TYPE, TCX_TYPE] )
def test_find( db ):
	# find by ids
	assert db.find_by_id( [] ) == []
	assert db.find_by_id( None ) == []
	assert db.find_by_id( [1, 2, 3, 999] ) == [db.get( id=1 ), db.get( id=2 ), db.get( id=3 )]

	# find by uids
	assert db.find_by_uid( [] ) == []
	assert db.find_by_uid( None ) == []
	assert db.find_by_uid( ['group:1001'] ) == [db.get( id=1 )]

	# find for uid
	assert db.find_for_uid( None ) == []
	assert ids( db.find_for_uid( 'polar:1001' ) ) == [1, 2]
	assert ids( db.find_for_uid( 'strava:1001' ) ) == [1, 3]

	# find groups by uid
	assert db.find_groups_for_uid( None ) == []
	assert db.find_groups_for_uid( 'polar:1001' ) == [db.get( id=1 )]
	assert db.find_groups_for_uid( 'strava:1001' ) == [db.get( id=1 )]

	# find resources
	assert db.find_resources_by_uid( 'polar:1001' ) == db.get( id=2 ).resources
	assert db.find_resources_by_uids( ['polar:1001', 'strava:1001'] ) == [*db.get( id=2 ).resources, *db.get( id=3 ).resources]

	resources = db.find_resources_of_type( GPX_TYPE )
	assert len( resources ) > 0 and all( [ r.type == GPX_TYPE for r in resources ] )

	summaries = db.find_summaries( 'polar:1001' )
	assert len( summaries ) == 1 and summaries[0].path == 'polar/1/0/0/1001/1001.json'
	summaries = db.find_all_summaries( ['polar:1001', 'strava:1001'] )
	assert [s.path for s in summaries] == ['polar/1/0/0/1001/1001.json', 'strava/1/0/0/1001/1001.json']

	recordings = db.find_recordings( 'polar:1001' )
	assert len( recordings ) == 1 and recordings[0].path == 'polar/1/0/0/1001/1001.gpx'
	recordings = db.find_all_recordings( ['polar:1001', 'strava:1001'] )
	assert [r.path for r in recordings] == ['polar/1/0/0/1001/1001.gpx', 'strava/1/0/0/1001/1001.gpx']

@mark.xfail
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

from datetime import datetime
from typing import List, Union

from dateutil.tz import UTC
from fs.errors import ResourceReadOnly
from fs.memoryfs import MemoryFS
from pytest import mark, raises

from test.objects import DEFAULT_ONE
from tracs.activity import Activity
from tracs.db import ActivityDb
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.polar import POLAR_FLOW_TYPE
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.tcx import TCX_TYPE
from tracs.resources import Resource
from tracs.uid import UID

@mark.unit
def test_db_with_fs():
	db = ActivityDb( fs=MemoryFS() )
	assert sorted( db.fs.listdir( '/' ) ) == ['activities.json', 'groups.json', 'multiparts.json', 'schema.json']
	assert db.schema == 15

@mark.unit
@mark.context( env='empty', persist='clone', cleanup=True )
def test_db_with_path( db_path ):
	db = ActivityDb( path=db_path )
	assert sorted( db.fs.listdir( '/' ) ) == ['activities.json', 'groups.json', 'multiparts.json', 'schema.json']
	assert db.schema == 15

@mark.unit
@mark.context( env='empty', persist='clone', cleanup=True )
def test_db_with_readonly_path( db_path ):
	db = ActivityDb( path=db_path, read_only=True )
	assert sorted( db.fs.listdir( '/' ) ) == ['activities.json', 'groups.json', 'multiparts.json', 'schema.json']
	assert db.schema == 15

	with raises( ResourceReadOnly ):
		db.fs.writetext( 'file.txt', '' )

@mark.unit
@mark.context( env='default', persist='clone', cleanup=True )
def test_open_db( db ):
	assert db.schema == 15
	assert len( db.activities ) > 1

	# todo: improve this test case
	# assert db.activities[0] == DEFAULT_ONE

@mark.unit
@mark.context( env='empty', persist='clone', cleanup=True )
def test_insert_upsert_remove( db ):
	assert len( db.activities ) == 0 and len( db.resources ) == 0

	a1 = Activity( uid='a:1', starttime=datetime( 2024, 3, 1, 10, 0, 0, tzinfo=UTC ) )
	a2 = Activity( uid='a:2' )
	a3 = Activity( uid='a:3' )

	# insert activities and check keys
	id = db.insert( a1 )
	assert a1.id == 1 and id == 1

	ids = db.insert_all( [a2, a3] )
	assert [ a.id for a in db.activities ] == [ 1, 2, 3 ] and ids == [2, 3]
	assert db.activity_keys == [1, 2, 3]

	# upsert
	dt = datetime( 2024, 3, 1, 10, 0, 0, tzinfo=UTC )
	a1 = Activity( name='one', uid='one:101', starttime=dt )
	a2 = Activity( name='two', uid='one:101', calories=100, starttime=dt )

	# like insert
	id = db.upsert( a1 )
	assert id == 4
	assert db.activity_keys == [1, 2, 3, 4]

	# update a1 with a2
	id = db.upsert( a2 )
	assert id == 4
	a = db.get_by_id( 4 )
	assert a.name == 'two' and a.uid == 'one:101' and a.calories == 100 and a.starttime == dt

	# upsert with group
#	grp = db.get_by_id( 4 )
#	grp.name, grp.uid, grp.calories = 'group', 'group:101', None
#	grp.metadata.members = [ UID( 'one:101' ), UID( 'one:102' ) ]

#	id = db.upsert( a2 )
#	assert id == 4
#	a = db.get_by_id( 4 )
#	assert a.name == 'group' and a.uid == 'group:101' and a.calories == 100 and a.starttime == dt

@mark.unit
@mark.context( env='default', persist='clone', cleanup=True )
def test_contains( db ):
	# test contains_activity
	assert db.contains_activity( uid='polar:7537918051' )
	assert not db.contains_activity( uid='polar:999999' )

	# this calls contains_activity based on UID
	assert db.contains( 'polar:7505780534' )
	assert not db.contains( 'polar:999999' )

	# test contains_resource
	assert db.contains_resource( uid='polar:7505780534', path='polar/7/5/0/7505780534/7505780534.gpx' )
	assert db.contains_resource( uid='polar:7505780534', path='7505780534.gpx' )
	assert not db.contains_resource( uid='polar:7505780534', path='polar/7/5/0/7505780534/7505780534.xxx' )
	assert not db.contains_resource( uid='polar:7505780534', path='7505780534.xxx' )

	# this calls contains_resource based on UID
	assert db.contains( uid='polar:7505780534/7505780534.gpx' )
	assert not db.contains( uid='polar:7505780534/7505780534.xxx' )

@mark.unit
@mark.context( env='default', persist='clone', cleanup=True )
@mark.db( summary_types=[POLAR_FLOW_TYPE, STRAVA_TYPE], recording_types=[GPX_TYPE, TCX_TYPE] )
def test_get( db ):
	# get activity by id
	a = db.get_by_id( 5 )
	assert a.id == 5 and a.uid == 'polar:7505780534'

	# non-existing id
	assert db.get_by_id( 0 ) is None and db.get_by_id( 9999 ) is None

	# existing activity
	assert db.get_by_uid( 'polar:7505780534' ).id == 5

	# non-existing polar activity
	assert db.get_by_uid( 'polar:9999999' ) is None

	# get groups
	# assert db.get_group_for( 'polar:1001' ).id == 1

	# get resource
	# assert db.get_resource_by_uid_path( 'polar:1001', 'polar/1/0/0/1001/1001.gpx' ) == db.get_by_id( 2 ).resources[0]

@mark.unit
@mark.context( env='default', persist='clone', cleanup=True )
@mark.db( summary_types=[POLAR_FLOW_TYPE, STRAVA_TYPE], recording_types=[GPX_TYPE, TCX_TYPE] )
def test_find( db ):
	# find by ids
	assert db.find_by_id( [] ) == []
	assert db.find_by_id( [1, 2, 3, 999] ) == [db.get( id=1 ), db.get( id=2 ), db.get( id=3 )]

	# find by uids
	assert db.find_by_uid( [] ) == []
	assert db.find_by_uid( ['polar:7505780534'] ) == [db.get( id=5 )]

	# find for uid
#	assert db.find_for_uid( None ) == []
#	assert ids( db.find_for_uid( 'polar:1001' ) ) == [1, 2]
#	assert ids( db.find_for_uid( 'strava:1001' ) ) == [1, 3]

	# find groups by uid
	grp = db.get_by_id( 30 )
	assert db.find_groups_for( 'polar:7505780534' ) == [grp]
	assert db.find_groups_for( 'strava:7973155107' ) == [grp]

	# # find resources
	# assert db.find_resources_by_uid( 'polar:1001' ) == db.get( id=2 ).resources
	# assert db.find_resources_by_uids( ['polar:1001', 'strava:1001'] ) == [*db.get( id=2 ).resources, *db.get( id=3 ).resources]
	#
	# resources = db.find_resources_of_type( GPX_TYPE )
	# assert len( resources ) > 0 and all( [ r.type == GPX_TYPE for r in resources ] )
	#
	# # find uids
	# assert 'polar:1001' in db.find_uids()
	# assert db.find_uids( 'waze' ) == [ 'waze:210111120000' ]
	#
	# summaries = db.find_summaries( 'polar:1001' )
	# assert len( summaries ) == 1 and summaries[0].path == 'polar/1/0/0/1001/1001.json'
	# summaries = db.find_summaries( 'polar:1001', 'strava:1001' )
	# assert [s.path for s in summaries] == ['polar/1/0/0/1001/1001.json', 'strava/1/0/0/1001/1001.json']
	#
	# recordings = db.find_recordings()
	# assert all( [ r.type in [GPX_TYPE, TCX_TYPE] for r in recordings ] )
	#
	# recordings = db.find_recordings( 'polar:1001' )
	# assert len( recordings ) == 1 and recordings[0].path == 'polar/1/0/0/1001/1001.gpx'
	# recordings = db.find_recordings( 'polar:1001', 'strava:1001' )
	# assert [r.path for r in recordings] == ['polar/1/0/0/1001/1001.gpx', 'strava/1/0/0/1001/1001.gpx']

# helper

def ids( elements: List[Union[Activity,Resource]] ) -> List[int]:
	return sorted( [e.id for e in elements] )

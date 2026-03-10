from logging import getLogger

from pytest import mark, raises

from test.objects import activity
from tracs.activity import Activities, Activity
from tracs.core import Metadata
from tracs.resources import Resource, Resources
from tracs.uid import UID, uid, uids

log = getLogger( __name__ )

@mark.unit
def test_activities():
	activities = Activities()
	a1, a2 = activity( 1 ), activity( 2 )
	a34 = [ activity( 3 ), activity( 4 ) ]
	assert activities.add( a1, a2 ) == [1, 2]
	assert activities.add( lst=a34 ) == [3, 4]
	assert len( activities ) == 4

	# convenience constructor
	activities = Activities( a1, a2, lst=a34 )
	assert len( activities ) == 4

	# re-adding will fail
	with raises( KeyError ):
		activities.add( a1 )

	# skip checks
	with raises( KeyError ):
		unchecked = Activities( Activity( id=10 ) )
	unchecked = Activities( Activity( id=10 ), skip_checks=True )
	assert unchecked[0].id is 10 and unchecked[0].uid is None

	# get
	assert activities.get_by_id( 1 ) == a1
	assert activities.get_by_id( 999 ) is None
	assert activities.get_by_uid( 'activity:1' ) == a1
	assert activities.get_by_uid( uid( 'activity:1' ) ) == a1
	assert activities.get_by_uid( 'activity:999' ) is None

	# contains
	assert a1 in activities
	assert uid( 'activity:1' ) in activities
	assert not 'something' in activities

	#
	assert activities.ids() == [ 1, 2, 3, 4]
	assert activities.uids() == uids( 'activity:1', 'activity:2', 'activity:3', 'activity:4' )

	assert activities.id_map == {
		1: a1, 2: a2, 3: a34[0], 4: a34[1]
	}
	assert activities.uid_map == {
		'activity:1': a1, 'activity:2': a2, 'activity:3': a34[0], 'activity:4': a34[1]
	}

	# all
	assert activities.all() == [ a1, a2, *a34 ]
	assert activities.all( sort=True, reverse=True ) == [ a34[1], a34[0], a2, a1 ]
	assert activities.all( sort=lambda a: a.name, reverse=True ) == [ a34[1], a34[0], a2, a1 ]

	# remove
	activities.remove( a34[1] )
	assert activities.get_by_id( 4 ) is None
	del( activities[2] )
	assert activities.get_by_id( 3 ) is None
	activities.remove( a2.uid )
	assert activities.get_by_id( 2 ) is None

	# # replace based on old activity
	# activities.replace( Activity( name='a2', uid='a:2' ), a1 )
	# assert len( activities ) == 1 and activities.idget( 1 ).name == 'a2'
	#
	# # replace based on id
	# activities.replace( Activity( name='a3', uid='a:3' ), id=1 )
	# assert len( activities ) == 1 and activities.idget( 1 ).name == 'a3'
	#
	# # replace based on uid
	# activities.replace( Activity( name='a4', uid='a:4' ), uid='a:3' )
	# assert len( activities ) == 1 and activities.idget( 1 ).name == 'a4'
	#
	# # replace based on id of new activity only
	# activities.replace( Activity( name='a5', uid='a:5', id=1 ) )
	# assert len( activities ) == 1 and activities.idget( 1 ).name == 'a5'
	#
	# # replace based on uid of new activity only
	# activities.replace( Activity( name='a6', uid='a:5' ) )
	# assert len( activities ) == 1 and activities.idget( 1 ).name == 'a6'

@mark.unit
def test_iter_activities():
	activities = Activities()
	a1 = Activity(
		name='a1', uid='a:1',
		resources = Resources( Resource( uid='a:1', path='a1.gpx' ), Resource( uid='a:1', path='a1.json' ) )
	)
	a2 = Activity(
		name='a2', uid='a:2',
		resources = Resources( Resource( uid='a:2', path='a2.gpx' ), Resource( path='a2.json' ) ) # no uid in a2.json!!
	)
	g1 = Activity(
		name='g34', uid='g:34',
		metadata = Metadata( members = [ UID( 'a:3' ), UID( 'a:4' ) ] ),
		resources = Resources( Resource( uid='a:3', path='a3.gpx' ), Resource( uid='a:4', path='a4.gpx' ) )
	)

	activities.add( a1 )
	activities.add( a2 )
	activities.add( g1 )

	assert [ it.uid for it in iter( activities ) ] == [ 'a:1', 'a:2', 'g:34' ]
	assert [ it.uid for it in activities.iter() ] == [ 'a:1', 'a:2', 'g:34' ]
	assert [ it.path for it in activities.iter_resources() ] == ['a1.gpx', 'a1.json', 'a2.gpx', 'a2.json', 'a3.gpx', 'a4.gpx']
	assert [ uid.uid for uid in activities.iter_uids() ] == [ 'a:1', 'a:2', 'g:34', 'a:3', 'a:4' ]
	assert [ uid.uid for uid in activities.iter_resource_uids() ] == [
		'a:1/a1.gpx', 'a:1/a1.json', 'a:2/a2.gpx', 'a:2/a2.json', 'a:3/a3.gpx', 'a:4/a4.gpx'
	]

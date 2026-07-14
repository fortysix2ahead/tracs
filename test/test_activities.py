from logging import getLogger

from pytest import mark, raises

from activity import ActivityGroup, MultipartActivity
from test.objects import activity
from tracs.activity import Activities, Activity
from tracs.core import Metadata
from tracs.uid import UID, uid, uids

log = getLogger( __name__ )

@mark.unit
def test_activities():
	activities = Activities()
	a1, a2 = activity( 1 ), activity( 2 )
	a34 = [ activity( 3 ), activity( 4 ) ]
	assert activities.add( a1 ) == 1
	assert activities.add( a2 ) == 2
	assert activities.add_all( a34 ) == [3, 4]
	assert len( activities ) == 4

	# convenience constructor
	activities = Activities( a1, a2, *a34 )
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
	assert UID.of( 'activity:1' ) in activities
	assert 'activity:1' in activities
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
	activities = Activities(
		a1 := Activity(
			name='activity_1', uid=UID.of( 'act:1' ), id=1,
			metadata = Metadata( member_of=UID.of( 'group:1' ) ),
		),
		a2 := Activity(
			name='activity_2', uid=UID.of( 'act:2' ), id=2,
			metadata = Metadata( member_of=UID.of( 'group:1' ) ),
		),
		a3 := Activity(
			name='activity_3', uid=UID.of( 'act:3' ), id=3,
			metadata=Metadata( part_of=[ UID.of( 'multipart:1' ) ] ),
		),
		a4 := Activity(
			name='activity_4', uid=UID.of( 'act:4' ), id=4,
			metadata = Metadata( part_of=[UID.of( 'multipart:1' )] ),
		),
		g1 := ActivityGroup(
			name='group_1', uid='group:1', id=10,
			metadata = Metadata( members = [ UID.of( 'act:1' ), UID.of( 'act:2' ) ] ),
		),
		mp11 := MultipartActivity(
			name='multi_1', uid='multi:1', id=20,
			metadata=Metadata( parts=[UID.of( 'act:3' ), UID.of( 'act:4' )] ),
		)
	, skip_checks = True )

	# normal iter()
	assert [ it.uid for it in iter( activities ) ] == ['act:1', 'act:2', 'act:3', 'act:4', 'group:1', 'multi:1']
	assert [ it.uid for it in activities.iter() ] == ['act:1', 'act:2', 'act:3', 'act:4', 'group:1', 'multi:1']

	# restrict to regular activities
	assert [ it.uid for it in activities.iter_regular() ] == ['act:1', 'act:2', 'act:3', 'act:4']

	# restrict to groups
	assert [ it.uid for it in activities.iter_groups() ] == ['group:1']

	# restrict to multiparts
	assert [ it.uid for it in activities.iter_multiparts() ] == ['multi:1']

	# restrict to non-groups
	assert [ it.uid for it in activities.iter_non_groups() ] == ['act:1', 'act:2', 'act:3', 'act:4', 'multi:1']

	# iterator for classifier
	assert [ it.uid for it in activities.iter_classifier( 'act' ) ] == ['act:1', 'act:2', 'act:3', 'act:4']

	# iterator for 'regular' unique activities
	assert [ it.uid for it in activities.iter_unique() ] == ['act:3', 'act:4', 'group:1']

	# iterate uids
	assert list( activities.iter_uids() ) == [ UID.of( u ) for u in [ 'act:1', 'act:2', 'act:3', 'act:4', 'group:1', 'multi:1' ] ]

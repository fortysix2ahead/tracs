
from datetime import datetime, time, timedelta
from logging import getLogger

from dateutil.tz import UTC
from pytest import mark, raises

from tracs.activity import Activities, Activity, ActivityGroup, groups, MultipartActivity
from tracs.activity_types import ActivityTypes
from tracs.core import Metadata, VirtualField
from tracs.pluginmgr import virtualfield
from tracs.resources import Resource, Resources
from tracs.uid import UID, uid, uids

log = getLogger( __name__ )

# noinspection PyUnresolvedReferences
def setup_module( module ):
	import tracs.plugins.keywords
	log.info( 'importing tracs.plugins.keywords' )

@mark.unit
def test_activity():
	a = Activity( uid=uid( 'polar:100' ) )
	assert a.uid == UID( classifier='polar', local_id=100 )
	assert a.uids == [ 'polar:100' ]
	assert a.classifier == 'polar'
	# assert a.refs() == ['polar:100'] and a.refs( True ) == [UID( 'polar:100' )]
	assert a.classifiers == ['polar']

	assert not a.group
	assert not a.multipart

@mark.unit
def test_activity_group():
	a = ActivityGroup(
		uid = uid( 'group:101' )
	)
	a.metadata.members = uids( 'strava:100', 'polar:100', 'polar:100' )

	assert a.group
	assert not a.multipart

	assert a.uid == 'group:101'
	assert a.uids == [ 'polar:100', 'strava:100' ]
#	assert a.refs() == [ 'polar:100', 'strava:100' ]
#	assert a.refs( True ) == [ UID( 'polar:100' ), UID( 'strava:100' ) ]
	assert a.classifiers == [ 'polar', 'strava' ]

@mark.unit
def test_union():
	a1 = Activity(
		id=1,
		name='One',
		distance=10,
		uid='polar:1',
		type=ActivityTypes.walk,
		starttime=datetime( 2024, 2, 1, 10, 0, 0 ),
		tags=['a'],
	)
	a2 = Activity(
		id=2,
		name='Two',
		calories=20,
		uid='polar:2',
		starttime = datetime( 2024, 2, 1, 10, 1, 0 ),
		tags=['b'],
		type=ActivityTypes.run,
	)

	u = Activity.union( a1, a2 )
	assert u.name == 'One' and u.distance == 10 and u.calories == 20
	assert u.uid == 'polar:1' and u.uids == [ 'polar:1' ]
	assert u.type == ActivityTypes.walk and u.tags == [ 'a', 'b' ]

	# union with force == True
	u = Activity.union( a1, a2, force=True )
	assert u.name == 'Two' and u.distance == 10 and u.calories == 20
	assert u.uid == 'polar:2' and u.uids == ['polar:2']
	assert u.type == ActivityTypes.run and u.tags == ['a', 'b']

@mark.unit
def test_group_of():
	src1 = Activity(
		id=1,
		name='One',
		uid=uid( 'polar:1' ),
		type=ActivityTypes.walk,
		starttime=datetime( 2024, 2, 1, 10, 0, 0 ),
		tags=['a'],
	)
	src2 = Activity(
		id=2,
		name='Two',
		distance=10,
		calories=20,
		uid=uid( 'polar:2' ),
		starttime = datetime( 2024, 2, 1, 10, 1, 0 ),
		tags=['b'],
	)

	g1 = ActivityGroup( id=3, calories=100, heartrate=100, name='Group One', uid='group:1' )
	g1.metadata.members = uids( 'polar:1', 'polar:2')

	g2 = ActivityGroup( id=4, calories=200, heartrate=200, name='Group Two', uid='group:2' )
	g2.metadata.members = uids( 'polar:1', 'polar:2' )

	# grouping
	group = ActivityGroup.of( src1, src2 )
	assert group.name == 'One' and group.distance == 10 and group.calories == 20
	assert group.uid == 'group:240201100000' and group.uids == [ 'polar:1', 'polar:2' ]
	assert group.type == ActivityTypes.walk

	# grouping with force
	group = ActivityGroup.of( src1, src2, force=True )
	assert group.name == 'Two' and group.distance == 10 and group.calories == 20 and group.type == ActivityTypes.walk
	assert group.uid == 'group:240201100000' and group.uids == [ 'polar:1', 'polar:2' ]

	# grouping with ignored_fields
	group = ActivityGroup.of(src1, src2, ignored_fields=[ 'type' ] )
	assert group.name == 'One' and group.distance == 10 and group.calories == 20
	assert group.uid == 'group:240201100000' and group.uids == [ 'polar:1', 'polar:2' ]
	assert group.type is None

	# grouping with target
	group = ActivityGroup.of(src1, src2, target=g1 )
	assert group is g1
	assert group.name == 'Group One' and group.distance == 10 and group.calories == 100
	assert group.uid == 'group:240201100000' and group.uids == [ 'polar:1', 'polar:2' ]
	assert group.type == ActivityTypes.walk

	# grouping with target and force
	group = ActivityGroup.of( src1, src2, target=g2, force=True )
	assert group is g2
	assert group.name == 'Two' and group.distance == 10 and group.calories == 20
	assert group.uid == 'group:240201100000' and group.uids == ['polar:1', 'polar:2']
	assert group.type == ActivityTypes.walk

	# wrong target
	with raises( ValueError ):
		group = ActivityGroup.of( src1, src2, target=Activity() )

@mark.unit
def test_multipart_activity():
	swim_start = datetime( 2023, 7, 1, 10, 0, 0, tzinfo=UTC )
	swim_end = datetime( 2023, 7, 1, 10, 30, 0, tzinfo=UTC )
	bike_start = datetime( 2023, 7, 1, 10, 35, 0, tzinfo=UTC )
	bike_end = datetime( 2023, 7, 1, 11, 55, 0, tzinfo=UTC )
	run_start = datetime( 2023, 7, 1, 12, 5, 0, tzinfo=UTC )
	run_end = datetime( 2023, 7, 1, 13, 0, 0, tzinfo=UTC )
	a1 = Activity( uid='polar:101', name='swim', distance=1500, starttime=swim_start, endtime=swim_end )
	a2 = Activity( uid='polar:102', name='bike', distance=40000, starttime=bike_start, endtime=bike_end )
	a3 = Activity( uid='polar:102', name='run', distance=10000, starttime=run_start, endtime=run_end )

	tri = MultipartActivity.of( a1, a2, a3 )

	assert tri.multipart
	assert [ gap.seconds for gap in tri.gaps ] == [ 300, 600 ]
	assert tri.type == ActivityTypes.multisport
	assert tri.distance == 51500
	assert tri.starttime == swim_start
	assert tri.endtime == run_end

	# average is a bit more complicated ...

	bike_start = datetime( 2023, 7, 1, 10, 0, 0, tzinfo=UTC )
	bike_end = datetime( 2023, 7, 1, 12, 0, 0, tzinfo=UTC )
	run_start = datetime( 2023, 7, 1, 12, 0, 0, tzinfo=UTC )
	run_end = datetime( 2023, 7, 1, 13, 0, 0, tzinfo=UTC )
	a1 = Activity( uid='polar:101', name='bike', heartrate=120, starttime=bike_start, endtime=bike_end, duration=timedelta( hours=2 ) )
	a2 = Activity( uid='polar:102', name='run', heartrate=180, starttime=run_start, endtime=run_end, duration=timedelta( hours=1 ) )

	assert MultipartActivity.of( a1, a2 ).heartrate == 140

@mark.unit
def test_groups():
	g = Activity( uid='g:1' )
	g.metadata.members=UID.from_strs( [ 'p:1', 's:1' ] )
	ng = Activity( uid='ng:1' )

	assert groups( None ) == []
	assert groups( [g, ng] ) == [g]

@mark.unit
def test_resource():
	some_string = 'some string value'
	r = Resource( uid='polar:1', path='content.dat', content=some_string.encode( encoding='UTF-8' ) )
	assert type( r.content ) is bytes and len( r.content ) > 0
	assert r.as_text() == some_string

	r = Resource( uid='polar:1', path='content.dat', text=some_string )
	assert type( r.content ) is bytes and len( r.content ) > 0
	assert r.as_text() == some_string
	assert r.text == some_string

def test_fields( registry ):
	fields = Activity.fields()
	assert next( f for f in fields if f.name == 'name' )
	field_names = Activity.field_names()
	assert 'name' in field_names and '__parent__' not in field_names and 'weekday' not in field_names

	field_names = Activity.field_names( include_internal=True )
	assert 'name' in field_names and '__parent__' in field_names and 'weekday' not in field_names

	field_names = Activity.field_names( include_virtual=True )
	assert 'name' in field_names and '__parent__' not in field_names and 'weekday' in field_names

	assert Activity.field_type( 'name' ) == 'str'
	assert Activity.field_type( 'weekday' ) == int
	assert Activity.field_type( 'noexist' ) is None

@virtualfield
def lower_name() -> VirtualField:
	return VirtualField( 'lower_name', str, display_name='lower_name', factory=lambda a: a.name.lower() )

@virtualfield
def uppercase_name() -> VirtualField:
	return VirtualField( 'upper_name', str, display_name='upper_name', factory=lambda a: a.name.upper() )

@virtualfield
def title_name() -> VirtualField:
	return VirtualField( 'title_name', str, display_name='title_name', factory=lambda a: a.name.title() )

@virtualfield
def capitalized_name() -> VirtualField:
	return VirtualField( 'cap_name', str, display_name='cap_name', factory=lambda a: a.name.capitalize() )

def test_virtual_activity_fields( registry ):

	assert 'lower_name' in Activity.__vf__.keys()
	assert 'upper_name' in Activity.__vf__.keys()
	assert 'title_name' in Activity.__vf__.keys()
	assert 'cap_name' in Activity.__vf__.keys()

	vf = Activity.__vf__.get( 'lower_name' )
	assert vf.name == 'lower_name'

	a = Activity(
		name='Afternoon run in Berlin',
		type=ActivityTypes.run,
	)

	assert a.vf.lower_name == 'afternoon run in berlin'
	assert a.vf.upper_name == 'AFTERNOON RUN IN BERLIN'
	assert a.vf.title_name == 'Afternoon Run In Berlin'
	assert a.vf.cap_name == 'Afternoon run in berlin'

	Activity.__vf__['fixed_value'] = VirtualField( 'fixed_value', int, 10 )

	assert a.vf.fixed_value == 10

	with raises( AttributeError ):
		assert a.vf.does_not_exist == 10

	assert a.getattr( 'lower_name' ) == 'afternoon run in berlin'
	assert a.getattr( 'fixed_value' ) == 10
	assert a.getattr( 'does_not_exist', quiet=True ) is None

	with raises( AttributeError ):
		assert a.getattr( 'does_not_exist' ) is None

@virtualfield
def name() -> VirtualField:
	return VirtualField( 'name', str, display_name='name', factory=lambda a: 'override attempt for run' )

# don't allow overriding fields
def test_virtual_activity_field_override( registry ):

	a = Activity( id = 100, name='Run', type=ActivityTypes.run )

	assert 'name' in Activity.field_names( include_virtual=True )
	assert a.name == 'Run' and a.getattr( 'name' ) == 'Run'

def test_formatted_activity_fields():

	a1 = Activity( name='Morning Run in Berlin', type=ActivityTypes.run )
	a2 = Activity( name='Afternoon Walk in Berlin', type=ActivityTypes.walk )

	assert a1.format( 'name' ) == 'Morning Run in Berlin'
	assert a2.format( 'name' ) == 'Afternoon Walk in Berlin'

	Activity.field_formatters()['name'] = lambda s, a, b: s.lower()

	assert a1.format( 'name' ) == 'morning run in berlin'
	assert a2.format( 'name' ) == 'afternoon walk in berlin'

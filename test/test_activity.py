
from datetime import datetime, time, timedelta
from logging import getLogger
from typing import List, Optional

from pytest import mark, raises

from tracs.activity import Activities, Activity, ActivityPart, groups
from tracs.activity_types import ActivityTypes
from tracs.core import VirtualField
from tracs.pluginmgr import virtualfield
from tracs.resources import Resource
from tracs.uid import UID

log = getLogger( __name__ )

# noinspection PyUnresolvedReferences
def setup_module( module ):
	import tracs.plugins.rule_extensions
	log.info( 'importing tracs.plugins.rule_extensions' )

def test_activity():
	a = Activity( uid = 'polar:100' )
	assert a.as_uid() == UID( classifier='polar', local_id=100 )
	assert a.uids == [] and a.as_uids() == []
	assert a.refs() == ['polar:100'] and a.refs( True ) == [UID( 'polar:100' )]
	assert a.classifiers == ['polar']

	assert not a.group
	assert not a.multipart

	# explicitely set uids to None
	a.uids = None
	assert a.uids == []

	# test values
	a = Activity( uid='polar:101', heartrate=150, calories=1000 )
	assert a.values( 'uid', 'heartrate', 'calories', 'speed', 'xyz' ) == ['polar:101', 150, 1000, None, None]

def test_activity_group():
	a = Activity( uid = 'group:101', uids = ['strava:100', 'polar:100', 'polar:100'] )
	assert a.uid == 'group:101' and a.as_uid() == UID( 'group:101' )
	assert a.uids == [ 'polar:100', 'strava:100' ]
	assert a.as_uids() == [ UID( 'polar:100' ), UID( 'strava:100' ) ]
	assert a.refs() == [ 'polar:100', 'strava:100' ]
	assert a.refs( True ) == [ UID( 'polar:100' ), UID( 'strava:100' ) ]
	assert a.classifiers == [ 'polar', 'strava' ]

	assert a.group
	assert not a.multipart

def test_activity_part():
	p = ActivityPart( uids=[ 'polar:1234' ] )
	assert p.as_uids == [ UID( classifier='polar', local_id=1234 ) ]
	assert p.classifiers == [ 'polar' ]

	p = ActivityPart( uids=['polar:2345', 'polar:1234' ] )
	assert p.as_uids == [ UID( 'polar:1234' ), UID( 'polar:2345' ) ]
	assert p.classifiers == [ 'polar' ]

	p = ActivityPart( uids=['polar:2345/rec.gpx', 'polar:2345/rec.tcx', 'polar:1234'] )
	assert p.as_uids == [ UID( 'polar:1234' ), UID( 'polar:2345/rec.gpx' ), UID( 'polar:2345/rec.tcx' ) ]
	assert p.as_activity_uids == [ UID( 'polar:1234' ), UID( 'polar:2345' ) ]
	assert p.activity_uids == [ 'polar:1234', 'polar:2345' ]
	assert p.classifiers == [ 'polar' ]

def test_multipart_activity():
	from dateutil.tz import UTC
	swim_start = datetime( 2023, 7, 1, 10, 0, 0, tzinfo=UTC )
	swim_end = datetime( 2023, 7, 1, 10, 30, 0, tzinfo=UTC )
	bike_start = datetime( 2023, 7, 1, 10, 35, 0, tzinfo=UTC )
	bike_end = datetime( 2023, 7, 1, 11, 55, 0, tzinfo=UTC )
	run_start = datetime( 2023, 7, 1, 12, 0, 0, tzinfo=UTC )
	run_end = datetime( 2023, 7, 1, 13, 0, 0, tzinfo=UTC )
	a1 = Activity( uid='polar:101', name='swim', distance=1500, starttime=swim_start, endtime=swim_end )
	a2 = Activity( uid='polar:102', name='bike', distance=40000, starttime=bike_start, endtime=bike_end )
	a3 = Activity( uid='polar:102', name='run', distance=10000, starttime=run_start, endtime=run_end )

	tri = Activity.multipart_of( a1, a2, a3 )

	assert tri.multipart
	assert [ p.gap.seconds for p in tri.parts ] == [ 0, 300, 300 ]
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

	assert Activity.multipart_of( a1, a2 ).heartrate == 140

@mark.skip
def test_multipart_activity2():
	p1 = ActivityPart( uids=['polar:101' ], gap=time( 0, 0, 0 ) )
	p2 = ActivityPart( uids=['polar:102', 'strava:102' ], gap=time( 1, 0, 0 ) )
	a = Activity( parts=[ p1, p2 ] )

	assert a.multipart
	assert a.uids == [ 'polar:101', 'polar:102', 'strava:102' ]
	assert a.as_uids() == [ UID( 'polar:101' ), UID( 'polar:102' ), UID( 'strava:102' ) ]
	assert a.classifiers == [ 'polar', 'strava' ]

	p1 = ActivityPart( uids=['polar:101/swim.gpx' ], gap=time( 0, 0, 0 ) )
	p2 = ActivityPart( uids=['polar:101/bike.gpx' ], gap=time( 1, 0, 0 ) )
	p3 = ActivityPart( uids=['polar:101/run.gpx' ], gap=time( 1, 0, 0 ) )
	a = Activity( parts=[ p1, p2, p3 ] )

	assert a.multipart
	assert a.uids == [ 'polar:101' ]
	assert a.as_uids() == [ UID( 'polar:101' ) ]
	assert a.classifiers == [ 'polar' ]

def test_union():
	src1 = Activity( id=1, name='One', uid='a1' )
	src2 = Activity( id=2, distance=10, calories=20, uid='a2' )
	src3 = Activity( id=3, calories=100, heartrate= 100, uid='g1', uids=[ 'a1', 'a2' ] )

	target = src1.union( [src2, src3], copy=True )
	assert target.name == 'One' and target.distance == 10 and target.calories == 20 and target.heartrate == 100
	assert target.id == 1
	assert target.uid == 'a1'
	assert target.uids == []
	assert src1.distance is None # source should be untouched

	target = src1.union( others=[src2, src3], force=True, copy=True )
	assert target.name == 'One' and target.distance == 10 and target.calories == 100 and target.heartrate == 100
	assert target.id == 3
	assert target.uid == 'g1'
	assert target.uids == [ 'a1', 'a2' ]
	assert src1.distance is None # source should be untouched

	src1.union( [src2, src3], copy=False )
	assert src1.name == 'One' and src1.distance == 10 and src1.calories == 20 and src1.heartrate == 100
	assert src1.id == 1
	assert src1.uid == 'a1'
	assert src1.uids == []

	# test constructor
	src1 = Activity( id=1, name='One' )
	target = Activity( others=[src1, src2, src3] )
	assert target.name == 'One' and target.distance == 10 and target.calories == 20 and target.heartrate == 100
	assert target.id is None
	assert target.uid is None
	assert target.uids == []

def test_add():
	src1 = Activity( starttime=datetime( 2022, 2, 22, 7 ), distance=10, duration=timedelta( hours=1 ), heartrate_max=180, heartrate_min=100 )
	src2 = Activity( starttime=datetime( 2022, 2, 22, 8 ), distance=20, duration=timedelta( hours=1, minutes=20 ) )
	src3 = Activity( starttime=datetime( 2022, 2, 22, 9 ), heartrate_max=160, heartrate_min=80 )
	target = src1.add( others=[src2, src3], copy=True )

	assert target.starttime == datetime( 2022, 2, 22, 7 )
	assert target.endtime is None

	assert target.distance == 30
	assert target.ascent is None
	assert target.elevation_max is None

	assert target.duration == timedelta( hours=2, minutes=20 )
	assert target.duration_moving == timedelta( seconds=0 )
	assert target.heartrate_max == 180
	assert target.heartrate_min == 80

def test_activities():
	activities = Activities()
	a = Activity( name='a1', uid='a:1' )
	activities.add( a )
	assert len( activities ) == 1

	# replace based on old activity
	activities.replace( Activity( name='a2', uid='a:2' ), a )
	assert len( activities ) == 1 and activities.idget( 1 ).name == 'a2'

	# replace based on id
	activities.replace( Activity( name='a3', uid='a:3' ), id=1 )
	assert len( activities ) == 1 and activities.idget( 1 ).name == 'a3'

	# replace based on uid
	activities.replace( Activity( name='a4', uid='a:4' ), uid='a:3' )
	assert len( activities ) == 1 and activities.idget( 1 ).name == 'a4'

	# replace based on id of new activity only
	activities.replace( Activity( name='a5', uid='a:5', id=1 ) )
	assert len( activities ) == 1 and activities.idget( 1 ).name == 'a5'

	# replace based on uid of new activity only
	activities.replace( Activity( name='a6', uid='a:5' ) )
	assert len( activities ) == 1 and activities.idget( 1 ).name == 'a6'

def test_groups():
	g = Activity( uid='g:1', uids=[ 'p:1', 's:1' ] )
	ng = Activity( uid='ng:1' )

	assert groups( None ) == []
	assert groups( [g, ng] ) == [g]

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
	assert 'name' in field_names and '__parent__' in field_names and 'weekday' not in field_names

	field_names = Activity.field_names( include_internal=False )
	assert 'name' in field_names and '__parent__' not in field_names and 'weekday' not in field_names

	field_names = Activity.field_names( include_virtual=True )
	assert 'name' in field_names and '__parent__' in field_names and 'weekday' in field_names

	assert Activity.field_type( 'name' ) == Optional[str]
	assert Activity.field_type( 'weekday' ) == int
	assert Activity.field_type( 'noexist' ) is None

@virtualfield
def lower_name( a: Activity ) -> str:
	return a.name.lower()

@virtualfield( name='upper_name' )
def uppercase_name( a: Activity ) -> str:
	return a.name.upper()

@virtualfield( name='title_name', type=str, description='titled activity name' )
def title_name( a: Activity ):
	return a.name.title()

@virtualfield( name='cap_name', description='capitalized activity name', type=str, display_name='Cap Name' )
def capitalized_name( a: Activity ):
	return a.name.capitalize()

def test_virtual_activity_fields( registry ):

	assert 'lower_name' in Activity.__vf__.__fields__.keys()
	assert 'upper_name' in Activity.__vf__.__fields__.keys()
	assert 'title_name' in Activity.__vf__.__fields__.keys()
	assert 'cap_name' in Activity.__vf__.__fields__.keys()

	vf = Activity.__vf__.__fields__['lower_name']
	assert vf.name == 'lower_name'

	a = Activity(
		name='Afternoon run in Berlin',
		type=ActivityTypes.run,
	)

	assert a.vf.lower_name == 'afternoon run in berlin'
	assert a.vf.upper_name == 'AFTERNOON RUN IN BERLIN'
	assert a.vf.title_name == 'Afternoon Run In Berlin'
	assert a.vf.cap_name == 'Afternoon run in berlin'

	Activity.__vf__.__fields__['fixed_value'] = VirtualField( 'fixed_value', int, 10 )

	assert a.vf.fixed_value == 10

	with raises( AttributeError ):
		assert a.vf.does_not_exist == 10

	assert a.getattr( 'lower_name' ) == 'afternoon run in berlin'
	assert a.getattr( 'fixed_value' ) == 10
	assert a.getattr( 'does_not_exist', quiet=True ) is None

	with raises( AttributeError ):
		assert a.getattr( 'does_not_exist' ) is None

@virtualfield
def name( a: Activity ) -> str:
	return 'override attempt for run'

# don't allow overriding fields
def test_virtual_activity_field_override( registry ):

	a = Activity( id = 100, name='Run', type=ActivityTypes.run )

	assert 'name' in Activity.__vf__.__fields__
	assert a.name == 'Run' and a.getattr( 'name' ) == 'Run'

def test_formatted_activity_fields():

	a1 = Activity( name='Morning Run in Berlin', type=ActivityTypes.run )
	a2 = Activity( name='Afternoon Walk in Berlin', type=ActivityTypes.walk )

	assert a1.fmf.__parent__ is a1
	assert a2.fmf.__parent__ is a2
	assert a1.fmf is a2.fmf # should reference the same instance

	assert a1.fmf.name == 'Morning Run in Berlin'
	assert a2.fmf.name == 'Afternoon Walk in Berlin'

	Activity.FMF()['name'] = lambda s, a, b: s.lower()

	assert a1.fmf.name == 'morning run in berlin'
	assert a2.fmf.name == 'afternoon walk in berlin'

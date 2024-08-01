from datetime import datetime, time, timedelta
from json import loads

from dateutil.tz import UTC
from pytest import mark
from rich.pretty import pprint

from activity import Activities, Activity, ActivityPart
from activity_types import ActivityTypes
from core import Metadata
from fsio import CONVERTER, load_activities, load_schema, write_activities
from uid import UID

A = Activity(
	id=1,
	uid='polar:101',
	starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
	duration=timedelta( hours=2 ),
	type=ActivityTypes.walk,
	metadata=Metadata(
		created = datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified = datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite = True,
		members = [ UID( 'polar:101' ), UID( 'strava:101' ) ],
	),
	parts=[ActivityPart( uids=['polar:222', 'polar:333'], gap=time( minute=20 ) )],
	location_country='de',
)

@mark.context( env='default', persist='mem' )
def test_load_schema( dbfs ):
	assert load_schema( dbfs ).version == 13

def test_load_write_uid():
	uid_str = 'polar:101/recording.gpx#1'
	uid = UID( uid_str )
	assert uid.to_str() == uid_str
	assert UID.from_str( uid_str ) == uid

def test_load_write_metadata():
	md = Metadata(
		created = datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified = datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite = True,
		members = [ UID( 'polar:101' ), UID( 'strava:101' ) ]
	)

	mdd = {
		'created': '2024-01-04T10:00:00+00:00',
		'favourite': True,
		'members': ['polar:101', 'strava:101'],
		'modified': '2024-01-04T11:00:00+00:00'
	}

	assert md.to_dict() == mdd
	assert Metadata.from_dict( mdd ) == md

def test_load_write_activity():
	ad = A.to_dict()
	A.from_dict( ad )
	pprint( ad )

@mark.context( env='default', persist='mem' )
def test_load_write_activities( dbfs ):
	# create test activity
	activities = Activities()

	a1 = Activity(
		id = 1,
		uid= 'polar:101',
		starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
		duration=timedelta( hours=2 ),
		type=ActivityTypes.walk,
		parts=[ActivityPart( uids=[ 'polar:222', 'polar:333' ], gap=time( minute=20 ) ) ],
	)
	a1.metadata.created = datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC )
	a1.metadata.favourite = True

	activities.add( a1 )

	# write to dbfs
	write_activities( activities, dbfs )

	json = loads( dbfs.readtext( 'activities.json' ) )
	assert json == [
		{
			'id': 1,
			'uid': 'polar:101',
			'duration': '02:00:00',
			'starttime': '2024-01-03T10:00:00+00:00',
			'type': 'walk',
			'metadata': {
				'created': '2024-01-04T10:00:00+00:00',
				'favourite': True
			},
			'parts': [
				{ 'gap': '00:20:00', 'uids': ['polar:222', 'polar:333'] }
			]
		}
	]

	#  load again from dbfs
	activities = load_activities( dbfs )

	assert len( activities ) == 1
	a1 = activities.values()[0]
	assert a1.id == 1 and a1.uid == 'polar:101'
	assert a1.duration == timedelta( hours=2 )
	assert a1.starttime == datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC )
	# assert a1.type == ActivityTypes.walk # don't know why this fails
	assert a1.type.name == 'walk'

	assert a1.parts[0].gap == time( minute=20 )
	assert a1.parts[0].uids == [ 'polar:222', 'polar:333' ]

	assert a1.metadata.created == datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC )
	assert a1.metadata.favourite

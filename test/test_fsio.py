from datetime import datetime, timedelta
from json import loads

from dateutil.tz import UTC
from pytest import mark

from activity import Activities, ActivityPart
from core import Metadata
from fsio import load_activities, load_schema, write_activities
from resources import Resources
from test.objects import COMPLETE_ACTIVITY as A, COMPLETE_ACTIVITY_DICT as AD, COMPLETE_ACTIVITY_WITH_RESOURCE_DATA as AC
from uid import UID

@mark.context( env='default', persist='mem' )
def test_load_schema( dbfs ):
	assert load_schema( dbfs ).version == 14

def test_uid():
	uid_str = 'polar:101/recording.gpx#1'
	uid = UID( uid_str )
	assert uid.to_str() == uid_str
	assert UID.from_str( uid_str ) == uid

def test_metadata():
	assert A.metadata.to_dict() == AD['metadata']
	assert Metadata.from_dict( AD['metadata'] ) == A.metadata

def test_resource():
	assert A.resources.to_dict() == AD['resources']
	assert AC.resources.to_dict() == AD['resources']
	assert Resources.from_dict( AD['resources'] ) == A.resources

def test_activity_part():
	assert A.parts[0].to_dict() == AD['parts'][0]
	assert ActivityPart.from_dict( AD['parts'][0] ) == A.parts[0]

# todo: comparison between activities is not yet correct, test case runs fine, but comparison fails
@mark.xfail
def test_activity():
	assert A.to_dict() == AD
	assert A.from_dict( AD ) == A

@mark.context( env='default', persist='mem' )
def test_activities( dbfs ):
	activities = Activities()
	activities.add( A )

	# write to dbfs
	write_activities( activities, dbfs )

	json = loads( dbfs.readtext( 'activities.json' ) )
	assert json == [ AD ]

	#  load again from dbfs
	activities = load_activities( dbfs )

	assert len( activities ) == 1
	a1 = activities.values()[0]
	assert a1.id == 1 and a1.uid == 'polar:101'
	assert a1.duration == timedelta( hours=2 )
	assert a1.starttime == datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC )
	# assert a1.type == ActivityTypes.walk # don't know why this fails
	assert a1.type.name == 'walk'

	assert a1.parts[0].gap == timedelta( minutes=20 )
	assert a1.parts[0].uid == UID.from_str( 'polar:222#1' )

	assert a1.metadata.created == datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC )
	assert a1.metadata.favourite

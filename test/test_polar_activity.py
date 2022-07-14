
from datetime import datetime
from datetime import time
from datetime import timezone

from dateutil.tz import tzlocal

from pytest import mark

from tracs.plugins.polar import PolarActivity
from tracs.activity_types import ActivityTypes

@mark.file( 'libraries/default/polar/1/0/0/100001/100001.raw.json' )
def test_init_from_raw( json ):
	pa = PolarActivity( raw=json )
	assert pa.raw_id == 100001
	assert pa.name == '00:25:34;0.0 km'
	assert pa.type == ActivityTypes.run
	assert pa.time == datetime( 2011, 4, 28, 15, 48, 10, tzinfo=timezone.utc )
	assert pa.localtime == datetime( 2011, 4, 28, 17, 48, 10, tzinfo=tzlocal() )
	assert pa.distance == 12000.3
	assert pa.duration == time( 0, 25, 35 )
	assert pa.calories == 456

@mark.file( 'libraries/default/polar/1/0/0/100012/100012.raw.json' )
def test_fitnessdata( json ):
	pa = PolarActivity( raw=json )
	assert pa.id == 0
	assert pa.raw_id == 100012

@mark.file( 'libraries/default/polar/1/0/0/100013/100013.raw.json' )
def test_orthostatic( json ):
	pa = PolarActivity( raw=json )
	assert pa.id == 0
	assert pa.raw_id == 100013

@mark.file( 'libraries/default/polar/1/0/0/100014/100014.raw.json' )
def test_rrrecording( json ):
	pa = PolarActivity( raw=json )
	assert pa.id == 0
	assert pa.raw_id == 100014

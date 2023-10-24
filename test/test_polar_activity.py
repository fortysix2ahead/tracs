
from datetime import datetime, timedelta
from datetime import timezone

from dateutil.tz import tzlocal
from pytest import mark

from tracs.activity_types import ActivityTypes
from tracs.plugins.polar import PolarFlowExercise
from tracs.plugins.polar import PolarFlowImporter

importer = PolarFlowImporter()

@mark.file( 'libraries/default/polar/1/0/0/100001/100001.json' )
def test_exercise( path ):
	resource = importer.load( path )
	pfe = resource.data
	assert pfe.local_id == 100001
	assert pfe.title == '00:25:34;0.0 km'
	assert pfe.type == 'EXERCISE'
	assert pfe.distance == 12000.3
	assert pfe.calories == 456

	pa = importer.as_activity( resource )
	assert pa.type == ActivityTypes.run
	assert pa.starttime == datetime( 2011, 4, 28, 15, 48, 10, tzinfo=timezone.utc )
	assert pa.starttime_local == datetime( 2011, 4, 28, 17, 48, 10, tzinfo=tzlocal() )
	assert pa.duration == timedelta(hours=0, minutes=25, seconds=34, microseconds=900000 )

@mark.file( 'libraries/default/polar/1/0/0/100012/100012.json' )
def test_fitnessdata( path ):
	r = importer.load( path )
	assert r.data.local_id == 100012
	assert r.data.index == 46

@mark.file( 'libraries/default/polar/1/0/0/100013/100013.json' )
def test_orthostatic( path ):
	r = importer.load( path )
	assert r.data.title == 'title'
	assert r.data.local_id == 100013
	assert r.data.datetime == '2016-09-28T21:11:04.000'

@mark.file( 'libraries/default/polar/1/0/0/100014/100014.json' )
def test_rrrecording( path ):
	r = importer.load( path )
	assert r.data.title == 'title'
	assert r.data.local_id == 100014
	assert r.data.datetime == '2017-01-16T21:34:58.000'


from datetime import datetime, timedelta, timezone

from dateutil.tz import tzlocal
from pytest import mark
from stravalib.model import DetailedActivity as StravaActivity

from test.helpers import skip_live
from tracs.activity_types import ActivityTypes
from tracs.plugins.strava import Strava
from tracs.plugins.strava.io import StravaHandler

importer = StravaHandler( activity_cls=StravaActivity )

@mark.file( 'environments/default/db/strava/7/9/7/7973155107/7973155107.json' )
def test_init_from_raw( path ):
	resource = importer.load( path )
	sa = importer.as_activity( resource )

	assert sa.id is None
	assert sa.classifiers == ['strava']
	assert sa.uid == 'strava:7973155107'
	assert sa.type == ActivityTypes.hiking
	assert sa.starttime == datetime( 2022, 10, 16, 12, 23, 40, tzinfo=timezone.utc )
	assert sa.starttime_local == datetime( 2022, 10, 16, 14, 23, 40, tzinfo=tzlocal() )
	assert sa.distance == 1150.3
	assert sa.speed == 0.653
	assert sa.speed_max == 2.486
	assert sa.ascent == 2.8
	assert sa.descent == 2.8
	assert sa.elevation_max == 235.2
	assert sa.elevation_min == 227.5
	assert sa.duration == timedelta( hours=3, minutes=13, seconds=1 )
	assert sa.duration_moving == timedelta( hours=0, minutes=29, seconds=22 )
	assert sa.heartrate == 0
	assert sa.heartrate_min is None
	assert sa.heartrate_max == 0
	assert sa.location_country is None

@skip_live
@mark.context( env='live', cleanup=False )
@mark.service( cls=Strava, init=True, register=True )
def test_import( service ):
	activities = service.import_activities( fetch_all=True )
	assert sorted( [ a.uid for a in activities ] ) == sorted( [
		'strava:8213576551', 'strava:8213576554', 'strava:8213576563', 'strava:8213576615',
		'strava:7973155107', 'strava:7956459613', 'strava:7956459639'
	] )


from datetime import datetime
from datetime import time
from datetime import timezone

from dateutil.tz import tzlocal
from pytest import mark

from tracs.activity_types import ActivityTypes
from tracs.plugins.strava import StravaActivity
from tracs.plugins.strava import StravaHandler

@mark.file( 'libraries/default/strava/2/0/0/200002/200002.json' )
def test_init_from_raw( path ):
	importer = StravaHandler( activity_cls=StravaActivity )
	resource = importer.load( path )
	sa = importer.as_activity( resource )

	assert sa.id is None
	assert sa.classifiers == ['strava']
	assert sa.uids == ['strava:200002']
	assert sa.type == ActivityTypes.run
	assert sa.starttime == datetime( 2018, 12, 16, 13, 15, 12, tzinfo=timezone.utc )
	assert sa.starttime_local == datetime( 2018, 12, 16, 14, 15, 12, tzinfo=tzlocal() )
	assert sa.distance == 8533.7
	assert sa.speed == 2.353
	assert sa.speed_max == 3.1
	assert sa.ascent == 81.0
	assert sa.descent == 81.0
	assert sa.elevation_max == 260.5
	assert sa.elevation_min == 202.4
	assert sa.duration == time( 0, 36, 25 )
	assert sa.duration_moving == time( 0, 33, 29 )
	assert sa.heartrate == 149
	assert sa.heartrate_min is None
	assert sa.heartrate_max == 171
	assert sa.location_country == 'Germany'

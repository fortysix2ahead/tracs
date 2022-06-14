
from datetime import datetime
from datetime import time
from datetime import timezone

from pytest import mark

from tracs.activity import ActivityRef
from tracs.activity_types import ActivityTypes
from tracs.plugins.strava import StravaActivity

@mark.db_template( 'default' )
def test_init_from_db( json ):
	sa = StravaActivity( json['activities']['3'], 3 )
	assert sa.groups == { "parent": 1 }
	assert sa.parent_id == 1
	assert sa.parent_uid == 'group:1'
	assert sa.parent_ref == ActivityRef( 1, 'group:1' )

	sa = StravaActivity( json['activities']['40'], 40 )

	assert sa.id == 40
	assert sa.uid == 'strava:20000000'
	assert sa.raw_id == 20000000
	assert sa.type == ActivityTypes.hike
	assert sa.time == datetime( 2019, 4, 22, 12, 4, 41, tzinfo=timezone.utc )
	assert sa.localtime == datetime( 2019, 4, 22, 14, 4, 41, tzinfo=timezone.utc )
	assert sa.distance == 8533.7
	assert sa.speed == 1.116
	assert sa.speed_max == 8.4
	assert sa.ascent == 237.7
	assert sa.descent == 237.7
	assert sa.elevation_max == 236.3
	assert sa.elevation_min == 117.2
	assert sa.duration == time( 3, 0, 39 )
	assert sa.duration_moving == time( 2, 7, 25 )
	assert sa.heartrate == 87.7
	assert sa.heartrate_min is None
	assert sa.heartrate_max == 151.0
	assert sa.location_country == 'Germany'

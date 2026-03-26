from typing import Any, Optional

from attrs import fields
from dateutil.tz import tzlocal
from stravalib.model import DetailedActivity as StravaActivity

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.cli import fields
from tracs.pluginmgr import importer
from tracs.plugins.json import JSONHandler
from tracs.plugins.strava.constants import STRAVA_TYPE, TYPES
from tracs.resources import Resource

@importer( type=STRAVA_TYPE )
class StravaHandler( JSONHandler ):

	TYPE: str = STRAVA_TYPE
	ACTIVITY_CLS = StravaActivity

	def load_data( self, raw: Any, **kwargs ):
		return StravaActivity.parse_obj( raw )

	def save_data( self, data: Any, **kwargs ) -> Any:
		return StravaActivity.dict( data )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		da: StravaActivity = resource.data
		tz_str = str( da.timezone ) if da.timezone else str( tzlocal() )

		# noinspection Py
		activity = Activity(
			name = da.name,
			type = TYPES.get( da.type.root, ActivityTypes.unknown ),
			starttime= da.start_date,
			starttime_local= da.start_date_local.astimezone( da.timezone.timezone() ),
			timezone = tz_str,
			distance = float( da.distance or 0.0 ),
			speed = float( da.average_speed or 0.0 ),
			speed_max = float( da.max_speed or 0.0 ),
			ascent = float( da.total_elevation_gain or 0.0 ),
			descent = float( da.total_elevation_gain or 0.0 ),
			elevation_max = float( da.elev_high or 0.0 ),
			elevation_min = float( da.elev_low or 0.0 ),
			duration = da.elapsed_time.timedelta(),
			duration_moving = da.moving_time.timedelta(),
			heartrate = int( da.average_heartrate or 0 ),
			heartrate_max = int( da.max_heartrate or 0 ),
			location_country = da.location_country,
			uid = f'strava:{da.id}',
		)

#		for f in fields( activity ):
#			if getattr( activity, f.name ) in [ 0, 0.0 ]:
#				setattr( activity, f.name, None )

		return activity


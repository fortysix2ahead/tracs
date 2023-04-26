
from logging import getLogger
from typing import Any, Optional, Union

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX

from tracs.activity import Activity
from tracs.registry import importer
from tracs.resources import Resource
from tracs.handlers import ResourceHandler
from tracs.utils import seconds_to_time

log = getLogger( __name__ )

GPX_TYPE = 'application/gpx+xml'

@importer( type=GPX_TYPE, activity_cls=GPX, recording=True )
class GPXImporter( ResourceHandler ):

	def load_data( self, content: Union[bytes,str], **kwargs ) -> Any:
		return parse_gpx( content )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		gpx: GPX = resource.raw
		return Activity(
			name = gpx.name,
			time = gpx.get_time_bounds().start_time.astimezone( UTC ),
			time_end = gpx.get_time_bounds().end_time.astimezone( UTC ),
			localtime = gpx.get_time_bounds().start_time.astimezone( tzlocal() ),
			localtime_end = gpx.get_time_bounds().end_time.astimezone( tzlocal() ),
			distance = round( gpx.length_2d(), 1 ),
			duration = seconds_to_time( gpx.get_duration() ) if gpx.get_duration() else None,
			location_latitude_start=gpx.get_points_data()[0].point.latitude,
			location_longitude_start=gpx.get_points_data()[0].point.longitude,
			location_latitude_end=gpx.get_points_data()[-1].point.latitude,
			location_longitude_end=gpx.get_points_data()[-1].point.longitude,
			# todo: don't add a gpx id as this field is currently of no use, maybe we can activate it later
			# uid = f'gpx:{gpx.get_time_bounds().start_time.astimezone( UTC ).strftime( "%y%m%d%H%M%S" )}',
		)

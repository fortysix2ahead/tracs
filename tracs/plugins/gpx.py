from datetime import timedelta
from logging import getLogger
from typing import Any, Optional, Union

from dateutil.tz import tzlocal, UTC
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX

from tracs.activity import Activity
from tracs.errors import ResourceImportException
from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, resourcetype
from tracs.resources import Resource, ResourceType

log = getLogger( __name__ )

GPX_TYPE = 'application/gpx+xml'

@resourcetype
def gpx_resource_type() -> ResourceType:
	return ResourceType( type=GPX_TYPE, recording=True )

@importer( type=GPX_TYPE )
class GPXImporter( ResourceHandler ):

	TYPE: str = GPX_TYPE
	ACTIVITY_CLS = GPX

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return parse_gpx( content )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		gpx: GPX = resource.raw
		gpx_activity = Activity( name = gpx.name )
		bounds = gpx.get_time_bounds()

		if not ( bounds.start_time and bounds.end_time ):
			raise ResourceImportException( 'GPX file is empty', None )
		else:
			gpx_activity.starttime= bounds.start_time.astimezone( UTC )
			gpx_activity.endtime= bounds.end_time.astimezone( UTC )
			gpx_activity.starttime_local= bounds.start_time.astimezone( tzlocal() )
			gpx_activity.endtime_local= bounds.end_time.astimezone( tzlocal() )

		gpx_activity.distance = round( gpx.length_2d(), 1 )
		gpx_activity.duration = timedelta( seconds=round( gpx.get_duration() ) ) if gpx.get_duration() == 0.0 else None

		if pd := gpx.get_points_data():
			gpx_activity.location_latitude_start=pd[0].point.latitude
			gpx_activity.location_longitude_start=pd[0].point.longitude
			gpx_activity.location_latitude_end=pd[-1].point.latitude
			gpx_activity.location_longitude_end=pd[-1].point.longitude
		gpx_activity.uid = f'gpx:{bounds.start_time.astimezone( UTC ).strftime( "%y%m%d%H%M%S" )}'

		return gpx_activity

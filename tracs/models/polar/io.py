from datetime import UTC
from itertools import zip_longest
from logging import getLogger
from typing import Any, List, Optional

from babel.dates import get_timezone
from dateutil.tz import tzlocal
from lxml.etree import tostring
from more_itertools import first

from tracs.activity import Activity
from tracs.models.io import polar_model_converter
from tracs.models.polar.constants import ACCESSLINK_TYPES, POLAR_SESSION_TYPE
from tracs.models.polar.training_session import TrainingSession
from tracs.pluginmgr import importer
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import DataclassFactoryHandler
from tracs.plugins.tcx import TCX_TYPE
from tracs.resources import Resource
from tracs.streams import Point, Stream
from tracs.utils import to_isotime

log = getLogger( __name__ )

@importer
class PolarTrainingSessionImporter( DataclassFactoryHandler ):

	TYPE: str = POLAR_SESSION_TYPE
	ACTIVITY_CLS = TrainingSession

	def __init__( self ):
		super().__init__()
		self.remainders: Optional[List[Activity]] = None

	def load_data( self, raw: Any, **kwargs ) -> Any:
		return super().load_data( raw, converter=polar_model_converter, cls=TrainingSession )

	def as_activity( self, resource: Resource ) -> Activity:
		for exc, act in zip( el := resource.data.get( 'exercises', [] ), activities := [Activity() for e in el] ):

			act.ascent = resource.float( 'ascent', parent=exc )
			act.cadence = resource.float( 'cadence', 'avg', parent=exc )
			act.cadence_max = resource.float( 'cadence', 'max', parent=exc )
			act.calories = resource.int( 'kiloCalories', parent=exc )
			act.descent = resource.float( 'descent', parent=exc )
			act.distance = resource.float( 'distance', parent=exc )
			act.duration = resource.td( 'duration', parent=exc )
			act.elevation = resource.float( 'altitude', 'avg', parent=exc )
			act.elevation_max = resource.float( 'altitude', 'max', parent=exc )
			act.elevation_min = resource.float( 'altitude', 'min', parent=exc )
			act.heartrate = resource.int( 'heartRate', 'avg', parent=exc )
			act.heartrate_max = resource.int( 'heartRate', 'max', parent=exc )
			act.heartrate_min = resource.int( 'heartRate', 'min', parent=exc )
			act.location_latitude_start = resource.float( 'latitude', parent=exc )
			act.location_longitude_start = resource.float( 'longitude', parent=exc )
			act.power = resource.float( 'power', 'avg', parent=exc )
			act.power_max = resource.float( 'power', 'max', parent=exc )
			act.speed = resource.float( 'speed', 'avg', parent=exc )
			act.speed_max = resource.float( 'speed', 'max', parent=exc )
			act.starttime = resource.utc( 'startTime', parent=exc )
			act.endtime = resource.utc( 'stopTime', parent=exc )

			# todo: actually this not always correct - when an activity took place in a different timezone than the home zone
			act.timezone = get_timezone().zone
			act.starttime_local = act.starttime.astimezone( tzlocal() )
			act.endtime_local = act.endtime.astimezone( tzlocal() )

			act.type = ACCESSLINK_TYPES.get( resource.strg( 'sport', parent=exc ) )

			# do not append, this is done in calling method automatically
			# act.resources.append( Resource(
			# 	content=resource.content,
			# 	type=POLAR_SESSION_TYPE,
			# ) )

			# create streams, todo: make this part more resilient, at the moment it's not clear what data can or cannot exist

			if samples := exc.get( 'samples' ):
				name, values = first( samples.items() )
				points = [Point() for p in range( len( values ) )]
				for pnt, fst, alt, dst, hr, rr, spd in zip_longest(
						points,
						samples.get( name, [] ),
						samples.get( 'altitude', [] ),
						# samples.get( 'cadence', [] ),
						samples.get( 'distance', [] ),
						samples.get( 'heartRate', [] ),
						# samples.get( 'leftPedalCrankBasedPower' ),
						samples.get( 'recordedRoute', [] ),
						samples.get( 'speed', [] ),
						# samples.get( 'strideLength' ),
						# samples.get( 'temperature' ),
						fillvalue={ }
				):
					pnt.time = to_isotime( fst.get( 'dateTime' ) ).astimezone( UTC )
					pnt.alt = alt.get( 'value', None )
					pnt.distance = dst.get( 'value', None )
					pnt.hr = hr.get( 'value', None )
					pnt.lat = rr.get( 'latitude', None )
					pnt.lon = rr.get( 'longitude', None )
					pnt.alt = rr.get( 'altitude', None )
					pnt.speed = spd.get( 'value', None )

				stream = Stream( points )
				gpx = stream.as_gpx()
				tcx = stream.as_tcx(
					average_heart_rate_bpm=act.heartrate,
					calories=act.calories,
					distance_meters=act.distance,
					# id=f'{summary.raw.get( "start_date_local" )}Z',
					intensity='Active',  # todo: don't know where to get this from
					maximum_heart_rate_bpm=act.heartrate_max,
					maximum_speed=act.speed_max,
					start_date=act.starttime,
					# trigger_method = 'Distance', # todo: this is not correct
					total_time_seconds=round( act.duration.total_seconds() ),
				)

				act.resources.append( Resource(
					content=gpx.to_xml( prettyprint=True ).encode( 'UTF-8' ),
					type=GPX_TYPE,
				) )
				act.resources.append( Resource(
					content=tostring( tcx.as_xml(), pretty_print=True ),
					type=TCX_TYPE,
				) )

		if len( activities ) == 1:  # if there's only one activity, we can return it directly -> main case
			self.remainders = None
			return first( activities )

		elif len( activities ) > 1:  # if there's more than one activity, we have to create a multipart activity
			parent_activity = Activity()
			self.remainders = activities  # save parts as remainders

			parent_activity.starttime = resource.utc( 'startTime' )
			parent_activity.endtime = resource.utc( 'stopTime' )
			parent_activity.duration = resource.td( 'duration' )
			parent_activity.distance = resource.float( 'distance' )
			parent_activity.heartrate = resource.int( 'averageHeartRate' )
			parent_activity.heartrate_max = resource.int( 'maximumHeartRate' )
			parent_activity.calories = resource.int( 'kiloCalories' )

			# "timeZoneOffset": 60 # todo: convert timezone offset into proper timezone
			parent_activity.timezone = get_timezone().zone
			parent_activity.starttime_local = parent_activity.starttime.astimezone( tzlocal() )
			parent_activity.endtime_local = parent_activity.endtime.astimezone( tzlocal() )

			# append main resource + recordings
			# parent_activity.resources.append( resource )
			return parent_activity

		else:  # can this happen?
			pass


from datetime import timedelta, UTC
from itertools import zip_longest
from logging import getLogger
from typing import Any, List, Optional, Tuple

from babel.dates import get_timezone
from dateutil.tz import tzlocal
from gpxpy.gpx import GPX
from lxml.etree import tostring
from more_itertools import first, first_true

from tracs.activity import Activity
from tracs.models.io import polar_model_converter
from tracs.models.polar.constants import *
from tracs.models.polar.training_session import Exercise, Route, Samples, TrainingSession
from tracs.pluginmgr import importer
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import DataclassFactoryHandler
from tracs.plugins.tcx import TCX_TYPE, TrainingCenterDatabase
from tracs.resources import Resource
from tracs.streams import Point, Stream
from tracs.uid import UID
from tracs.utils import millis_to_timedelta, to_isotime

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

	def as_activity( self, resource: Resource ) -> Activity | Tuple[Activity]:
		if len( resource.data.exercises ) == 1:
			return self._from_single_exercise( resource.data, resource.data.exercises[0] )
		else:
			parent, parts = self._from_multiple_exercises( resource.data, resource.data.exercises )
			return parent, *parts

		# for e, a in zip( el := resource.data.exercises, activities := [Activity() for e in el] ):
			# do not append, this is done in calling method automatically
			# act.resources.append( Resource(
			# 	content=resource.content,
			# 	type=POLAR_SESSION_TYPE,
			# ) )

		# if len( activities ) == 1:  # if there's only one activity, we can return it directly -> main case
		# 	self.remainders = None
		# 	return first( activities )

		# elif len( activities ) > 1:  # if there's more than one activity, we have to create a multipart activity
		# 	parent_activity = Activity()
		# 	self.remainders = activities  # save parts as remainders
		#
		# 	parent_activity.starttime = resource.utc( 'startTime' )
		# 	parent_activity.endtime = resource.utc( 'stopTime' )
		# 	parent_activity.duration = resource.td( 'duration' )
		# 	parent_activity.distance = resource.float( 'distance' )
		# 	parent_activity.heartrate = resource.int( 'averageHeartRate' )
		# 	parent_activity.heartrate_max = resource.int( 'maximumHeartRate' )
		# 	parent_activity.calories = resource.int( 'kiloCalories' )
		#
		# 	# "timeZoneOffset": 60 # todo: convert timezone offset into proper timezone
		# 	parent_activity.timezone = get_timezone().zone
		# 	parent_activity.starttime_local = parent_activity.starttime.astimezone( tzlocal() )
		# 	parent_activity.endtime_local = parent_activity.endtime.astimezone( tzlocal() )
		#
		# 	# append main resource + recordings
		# 	# parent_activity.resources.append( resource )
		# 	return parent_activity
		#
		# else:  # can this happen?
		# 	pass

	def _from_single_exercise( self, s: TrainingSession, e: Exercise ) -> Activity:
		a = Activity(
			ascent = e.ascentMeters,
			# not supported any longer?
			# cadence = resource.float( 'cadence', 'avg', parent=exc )
			# cadence_max = resource.float( 'cadence', 'max', parent=exc )
			calories = e.calories,
			descent = e.descentMeters,
			distance = e.distanceMeters,
			duration = millis_to_timedelta( e.durationMillis ),
			elevation = _statistic( e, STAT_ALT, 'avg' ),
			elevation_max = _statistic( e, STAT_ALT, 'max' ),
			elevation_min = _statistic( e, STAT_ALT, 'min' ),
			endtime = to_isotime( e.stopTime ),
			endtime_local = to_isotime( e.stopTime ).astimezone( tzlocal() ),
			heartrate = _statistic( e, STAT_HR, 'avg' ),
			heartrate_max = _statistic( e, STAT_HR, 'max' ),
			heartrate_min = _statistic( e, STAT_HR, 'min' ),
			location_latitude_start = e.latitude,
			location_longitude_start = e.longitude,
			# power values are hidden somewhere else now?
			# power = resource.float( 'power', 'avg', parent=exc )
			# power_max = resource.float( 'power', 'max', parent=exc )
			speed = _statistic( e, STAT_SPEED, 'avg' ),
			speed_max = _statistic( e, STAT_HR, 'max' ),
			starttime = to_isotime( e.startTime ),
			starttime_local = to_isotime( e.startTime ).astimezone( tzlocal() ),
			timezone = get_timezone().zone, # todo: this not correct - when an activity took place in a different timezone than the home zone
			type = ACCESSLINK_TYPES.get( e.sport.id ), # todo: this will fail, sports now have ids
			uid = UID( classifier=CLASSIFIER, local_id=int( e.identifier.id ) )
		)

		stream = self._stream( e.routes.route,  e.samples )

		# create GPX/TCX

		gpx, tcx = self._gpx_tcx( a, stream )

		# attach resources

		a.resources.append( Resource(
			name=f'gpx recording {a.uid.local_id}',
			content=gpx.to_xml( prettyprint=True ).encode( 'UTF-8' ),
			type=GPX_TYPE
		) )
		a.resources.append( Resource(
			name=f'tcx recording {a.uid.local_id}',
			content=tostring( tcx.as_xml(), pretty_print=True ),
			type=TCX_TYPE
		) )

		return a

	def _from_multiple_exercises( self, s: TrainingSession, el: List[Exercise] ) -> Tuple[Activity, Tuple[Activity]]:
		pass

	def _stream( self, route: Route, samples: Samples ) -> Stream:
		# todo: check this again: the length of the route list is samples length - 2
		# this means the first and the last points are missing? Or the first two?
		# in addition a waypoint does not contain a timestamp, but elapsedMillis, starting at 2xxx
		# this also means that this code will likely break for older takeouts?

		# assume that the second point is 1000 ms away from the start
		start = to_isotime( route.startTime )
		times = [ start, start + timedelta( milliseconds=1000 ), *[start + timedelta( wp.elapsedMillis ) for wp in route.wayPoints] ]

		# we'll triple the first point for now to have the same length as the samples lists
		# although this may not be correct, maybe there's a start and end point somewhere?
		# latitudes = [route.wayPoints[0].latitude, route.wayPoints[0].latitude, *[wp.latitude for wp in route.wayPoints]]
		# longitudes = [route.wayPoints[0].longitude, route.wayPoints[0].longitude, *[wp.longitude for wp in route.wayPoints]]

		# more correct is probably to mark the points as missing
		latitudes = [None, None, *[wp.latitude for wp in route.wayPoints]]
		longitudes = [None, None, *[wp.longitude for wp in route.wayPoints]]

		for tm, lat, lon, alt, dst, hr, spd, p in zip_longest(
			times,
			latitudes,
			longitudes,
			_sample_values( samples, SAMPLE_ALT ),
			# _sample_values( samples, SAMPLE_CADENCE ),
			_sample_values( samples, SAMPLE_DIST ),
			_sample_values( samples, SAMPLE_HR ),
			_sample_values( samples, SAMPLE_SPEED ),
			# _sample_values( samples, SAMPLE_STRIDE ),
			# _sample_values( samples, SAMPLE_TEMP ),
			points := list(),
		):
			points.append(
				Point( time=tm, lat=lat, lon=lon, alt=alt, distance=dst, hr=hr, speed=spd )
			)

		return Stream( points )

	def _gpx_tcx( self, a: Activity, stream: Stream ) -> Tuple[GPX, TrainingCenterDatabase]:
		gpx = stream.as_gpx()
		tcx = stream.as_tcx(
			average_heart_rate_bpm=a.heartrate,
			calories=a.calories,
			distance_meters=a.distance,
			# id=f'{summary.raw.get( "start_date_local" )}Z',
			intensity='Active',  # todo: don't know where to get this from
			maximum_heart_rate_bpm=a.heartrate_max,
			maximum_speed=a.speed_max,
			start_date=a.starttime,
			# trigger_method = 'Distance', # todo: this is not correct
			total_time_seconds=round( a.duration.total_seconds() ),
		)
		return gpx, tcx

def _statistic( e: Exercise, type: str, value: str ) -> float|int|None:
	# todo: exception handling
	return getattr( first_true( e.statistics.statistics, pred=lambda s: s.type == type ), value )

def _sample_len( samples: Samples ) -> int:
	return max( [len( s.values ) for s in samples.samples] )

def _sample_values( samples: Samples, type: str ) -> List[float]:
	return first_true( samples.samples, pred=lambda s: s.type == type ).values

from datetime import datetime, timedelta, UTC
from itertools import pairwise, zip_longest
from logging import getLogger
from typing import Any, List, Optional, Tuple

from babel.dates import get_timezone
from dateutil.tz import tzlocal
from gpxpy.gpx import GPX
from lxml.etree import tostring
from more_itertools import first, first_true
from more_itertools.recipes import all_equal

from test.objects import activity
from tracs.activity import Activity, MultipartActivity
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

	def load_data( self, raw: Any, **kwargs ) -> Any:
		return super().load_data( raw, converter=polar_model_converter, cls=TrainingSession )

	def as_activity( self, resource: Resource ) -> Activity|Tuple[Activity, ...]:
		if len( resource.data.exercises ) == 1:
			activity, parts = self._from_single_exercise( resource.data, resource.data.exercises[0] ), ()
		elif len( resource.data.exercises ) > 1:
			activity, parts = self._from_multiple_exercises( resource.data, resource.data.exercises )
		else:
			log.error( 'unable to import training session without exercises - this should not happen, please report this as bug' )
			raise NotImplementedError()

		# attach main resource to main activity
		resource.name=f'training session {activity.uid.local_id}'
		resource.path=f'{activity.uid.local_id}.json'
		activity.resources.insert( 0, resource )

		return activity, *parts

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

		stream = self._stream( e.routes.route,  e.samples, a.starttime )

		# create GPX/TCX
		gpx, tcx = self._gpx_tcx( a, stream )

		# attach resources
		gpx_resource = Resource(
			name=f'gpx recording {a.uid.local_id}',
			path=f'{a.uid.local_id}.gpx',
			content=gpx.to_xml( prettyprint=True ).encode( 'UTF-8' ),
			type=GPX_TYPE
		)
		tcx_resource = Resource(
			name=f'tcx recording {a.uid.local_id}',
			path=f'{a.uid.local_id}.tcx',
			content=tostring( tcx.as_xml(), pretty_print=True ),
			type=TCX_TYPE
		)
		a.resources.add_all( gpx_resource, tcx_resource )

		return a

	def _from_multiple_exercises( self, s: TrainingSession, el: List[Exercise] ) -> Tuple[MultipartActivity, Tuple[Activity, ...]]:
		parent = MultipartActivity(
			# ascent = no field
			# not supported any longer?
			# cadence = resource.float( 'cadence', 'avg', parent=exc )
			# cadence_max = resource.float( 'cadence', 'max', parent=exc )
			calories = s.calories,
			# descent = no field
			distance = s.distanceMeters,
			duration = millis_to_timedelta( s.durationMillis ),
			# elevation = no field
			# elevation_max = no field
			# elevation_min = no field
			endtime = to_isotime( s.stopTime ),
			endtime_local = to_isotime( s.stopTime ).astimezone( tzlocal() ),
			heartrate = s.hrAvg,
			heartrate_max = s.hrMax,
			# heartrate_min = no field exists,
			location_latitude_start = s.latitude,
			location_longitude_start = s.longitude,
			# power values are hidden somewhere else now?
			# power = resource.float( 'power', 'avg', parent=exc )
			# power_max = resource.float( 'power', 'max', parent=exc )
			name = s.name,
			# speed = no field
			# speed_max = no field
			starttime = to_isotime( s.startTime ),
			starttime_local = to_isotime( s.startTime ).astimezone( tzlocal() ),
			timezone = get_timezone().zone, # todo: this not correct - when an activity took place in a different timezone than the home zone
			type = ACCESSLINK_TYPES.get( s.sport.id ), # todo: this will fail, sports now have ids
			uid = UID( classifier=CLASSIFIER, local_id=int( s.identifier.id ) )
		)

		# extract parts
		parts = [ self._from_single_exercise( s, p ) for p in el ]

		# update members
		parent.metadata.members = [ p.uid for p in parts ]
		[ p.metadata.part_of.append( parent.uid ) for p in parts ]

		# assume the parts are already sorted by starttime
		parent.gaps = [ p2.endtime - p1.starttime for p1, p2 in pairwise( parts ) ]

		return parent, tuple( parts )

	# noinspection PyMethodMayBeStatic
	def _stream( self, route: Route, samples: Samples, start: datetime ) -> Stream:
		# the length of the route list may be samples length - 2 for an unknow reason
		# in this case the first two waypoints are missing and the third starts with elapsedMillis = 2xxx

		# in older exercises this seems to match, but the first wp.elapsedMillis is not 0, but None

		# use start time from route if it exists, otherwise rely on provided time
		if route is not None:
			start = to_isotime( route.startTime )
			# fix the missing first elapsed time stamp, if necessary
			elapsed_millis= [ wp.elapsedMillis for wp in route.wayPoints ]
			if elapsed_millis[0] is None:
				elapsed_millis[0] = 0
			times = [start + timedelta( milliseconds=t ) for t in elapsed_millis]

			log.debug( f'exercise contains a route with {len( times )} timestamps' )

			latitudes = [wp.latitude for wp in route.wayPoints]
			longitudes = [wp.longitude for wp in route.wayPoints]

			log.debug( f'route contains {len( latitudes )} coordinates' )

		else:
			millis, length = first( samples.samples ).intervalMillis, _sample_len( samples )
			times = [ start + timedelta( milliseconds=i*millis ) for i in range( length )]
			latitudes, longitudes = [], []

		_samples = [
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
		]

		# sanity check for lengths
		lengths = [ l for l in [len( s ) for s in _samples ] if l > 0]
		if not all_equal( lengths ):
			log.warning( 'lengths of samples do not match ... this requires further investigation ...' )

		for tm, lat, lon, alt, dst, hr, spd, p in zip_longest( *_samples, points := [] ):
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
	try:
		return getattr( first_true( e.statistics.statistics, pred=lambda s: s.type == type ), value )
	except AttributeError:
		# log.error( 'error', exc_info=True ) # used for development only, to examine data model
		pass

def _sample_len( samples: Samples ) -> int:
	return max( [len( s.values ) for s in samples.samples] )

def _sample_values( samples: Samples, type: str ) -> List[float]:
	try:
		return first_true( samples.samples, pred=lambda s: s.type == type ).values
	except AttributeError:
		return [] # empty in case samples do not exist

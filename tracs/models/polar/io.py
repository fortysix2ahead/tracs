from datetime import datetime, timedelta, UTC
from itertools import pairwise, zip_longest
from logging import getLogger
from re import compile
from typing import Any, Dict, List, Optional, Tuple

from babel.dates import get_timezone
from dateutil.tz import tzlocal
from gpxpy.gpx import GPX
from lxml.etree import tostring
from more_itertools import first, first_true
from more_itertools.recipes import all_equal

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

REGEX_UUID = compile( r'\w{8}-\w{4}-\w{4}-\w{4}-\w{12}' )

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
			# uid = UID( classifier=CLASSIFIER, local_id=int( s.identifier.id ) )
		)

		# update metadata

		if s.identifier.id != e.identifier.id:
			# for newer than 2026-03 exercises s.identifier.id is a UUID, that's why we're using e.id
			# the web url in Flow also points to e.id, but to s.id for older exercises
			if REGEX_UUID.match( s.identifier.id ):
				a.uid = UID( classifier=CLASSIFIER, local_id=int( e.identifier.id ) )

			# save the exercise id as custom metadata, for an unknown reason the id is different from the session id
			else:
				a.uid = UID( classifier=CLASSIFIER, local_id=int( s.identifier.id ) )
				a.metadata.set( 'exercise_id', str( e.identifier.id ) )

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
		parent.metadata.parts = [ p.uid for p in parts ]
		[ p.metadata.part_of.append( parent.uid ) for p in parts ]

		# assume the parts are already sorted by starttime
		parent.gaps = [ p2.endtime - p1.starttime for p1, p2 in pairwise( parts ) ]

		return parent, tuple( parts )

	# noinspection PyMethodMayBeStatic
	def _stream( self, route: Route, samples: Samples, start: datetime ) -> Stream:
		# the length of the route list may be samples_length - 2 for an unknown reason
		# in this case the first two waypoints are missing and the third starts with elapsedMillis = 2xxx
		# in older exercises this seems to match, but the first wp.elapsedMillis is not 0, but None

		# use start time from route if it exists, otherwise rely on provided time
		if route is not None:
			start = to_isotime( route.startTime )

		_points = {}

		_sample_values( samples, SAMPLE_ALT, _points )
		_sample_values( samples, SAMPLE_DIST, _points )
		_sample_values( samples, SAMPLE_HR, _points )
		_sample_values( samples, SAMPLE_SPEED, _points )

		_route_values( route, _points )

		for elapsed, point in _points.items():
			point.time = start + timedelta( milliseconds=elapsed )

		# sanity check for lengths
		_check_sample_lengths( samples, route )

		return Stream( sorted( _points.values(), key=lambda p: p.time ) )

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
	except (AttributeError, TypeError):
		# log.error( 'error', exc_info=True ) # used for development only, to examine data model
		pass

def _sample_len( samples: Samples ) -> int:
	return max( [len( s.values ) for s in samples.samples] )

def _route_values( route: Route, points: Dict ) -> None:
	try:
		for wp in route.wayPoints:
			elapsed = wp.elapsedMillis if wp.elapsedMillis else 0
			if not (p := points.get( elapsed )):
				p = Point()
				points[elapsed] = p

			p.lat, p.lon = wp.latitude, wp.longitude
			# p.alt = wp.altitude # todo: take altitude from here? is it different from samples?

	except (AttributeError, TypeError):
		pass

def _sample_values( samples: Samples, type: str, points: Dict ) -> None:
	try:
		sample = first_true( samples.samples, pred=lambda s: s.type == type )
		for i in range( len( sample.values ) ):
			millis = sample.intervalMillis * i

			if not (p := points.get( millis )):
				p = Point()
				points[millis] = p

			try:
				if type == SAMPLE_ALT:
					p.alt = sample.values[i]
				elif type == SAMPLE_DIST:
					p.distance = sample.values[i]
				elif type == SAMPLE_HR:
					p.hr = int( sample.values[i] )
				elif type == SAMPLE_SPEED:
					p.speed = sample.values[i]
			except ValueError:
				pass

	except (AttributeError, TypeError):
		pass

def _check_sample_lengths( samples: Samples, route: Route ):
	try:
		lengths = [ len( s.values ) for s in samples.samples ]
		lengths = [ *lengths, len( route.wayPoints ) ] if route else lengths
		if not all_equal( lengths ):
			log.warning( f'lengths of samples do not match, ranging from {min( lengths )} to {max( lengths )}. This requires further investigation ...' )
	except TypeError:
		pass

from datetime import datetime, timedelta, UTC
from itertools import pairwise
from logging import getLogger
from re import compile
from typing import Any, Dict, List, Optional, Tuple

from cattrs.preconf.orjson import OrjsonConverter
from dateutil.tz import tzlocal, tzoffset
from gpxpy.gpx import GPX
from lxml.etree import tostring
from more_itertools import first_true
from more_itertools.recipes import all_equal

from tracs.activity import Activity, MultipartActivity
from tracs.pluginmgr import importer
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.json import DataclassFactoryHandler
from tracs.plugins.polar.constants import *
from tracs.plugins.polar.models.training_session import Exercise, Route, Samples, TrainingSession
from tracs.plugins.tcx import TCX_TYPE, TrainingCenterDatabase
from tracs.resources import Resource
from tracs.streams import Point, Stream
from tracs.uid import UID
from tracs.utils import millis_to_timedelta, to_isotime, to_naive_time

log = getLogger( __name__ )

REGEX_UUID = compile( r'\w{8}-\w{4}-\w{4}-\w{4}-\w{12}' )


def to_floatstr( v, t ):
	return v if isinstance( v, float ) else float( v )

def make_polar_converter() -> OrjsonConverter:
	c = OrjsonConverter( omit_if_default=True, detailed_validation=True )

	# c.register_unstructure_hook( float|str, lambda v: str( v ) if isinstance( v, float ) else v )

	c.register_structure_hook( float|str, to_floatstr )

	return c

polar_model_converter = make_polar_converter()

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

	def _from_single_exercise( self, s: TrainingSession, e: Exercise, force_sid: bool = True ) -> Activity:
		a = Activity(
			ascent = e.ascentMeters,
			cadence = _statistic( e, STAT_CADENCE, 'avg' ),
			cadence_max = _statistic( e, STAT_CADENCE, 'max' ),
			calories = e.calories,
			descent = e.descentMeters,
			distance = e.distanceMeters,
			duration = millis_to_timedelta( e.durationMillis ),
			elevation = _statistic( e, STAT_ALT, 'avg' ),
			elevation_max = _statistic( e, STAT_ALT, 'max' ),
			elevation_min = _statistic( e, STAT_ALT, 'min' ),
			heartrate = _statistic( e, STAT_HR, 'avg' ),
			heartrate_max = _statistic( e, STAT_HR, 'max' ),
			heartrate_min = _statistic( e, STAT_HR, 'min' ),
			location_latitude_start = e.latitude,
			location_longitude_start = e.longitude,
			power = _statistic( e, STAT_POWER, 'avg' ),
			power_max = _statistic( e, STAT_POWER, 'max' ),
			speed = _statistic( e, STAT_SPEED, 'avg' ),
			speed_max = _statistic( e, STAT_HR, 'max' ),
			type = ACCESSLINK_TYPES.get( e.sport.id ), # todo: this will fail, sports now have ids
		)

		self._set_times( a, s, e )
		a.uid, metadata = self._uid_from_exercise( s, e, force_sid=force_sid )
		a.metadata.set( *metadata )

		stream = self._stream( e.routes.route,  e.samples, a.starttime )

		# create GPX/TCX
		gpx, tcx = self._gpx_tcx( a, stream )

		# attach resources

		if gpx:
			a.resources.append(
				Resource(
					name=f'gpx recording {a.uid.local_id}',
					path=f'{a.uid.local_id}.gpx',
					content=gpx.to_xml( prettyprint=True ).encode( 'UTF-8' ),
					type=GPX_TYPE
				)
			)

		if tcx:
			a.resources.append(
				Resource(
					name=f'tcx recording {a.uid.local_id}',
					path=f'{a.uid.local_id}.tcx',
					content=tostring( tcx.as_xml(), pretty_print=True ),
					type=TCX_TYPE
				)
			)

		return a

	def _from_multiple_exercises( self, s: TrainingSession, el: List[Exercise] ) -> Tuple[MultipartActivity, Tuple[Activity, ...]]:
		parent = MultipartActivity(
			# ascent = no field
			calories = s.calories,
			# descent = no field
			distance = s.distanceMeters,
			duration = millis_to_timedelta( s.durationMillis ),
			# elevation = no field
			# elevation_max = no field
			# elevation_min = no field
			heartrate = s.hrAvg,
			heartrate_max = s.hrMax,
			# heartrate_min = no field exists,
			location_latitude_start = s.latitude,
			location_longitude_start = s.longitude,
			name = s.name,
			# speed = no field
			# speed_max = no field
			type = ACCESSLINK_TYPES.get( s.sport.id ), # todo: this will fail, sports now have ids
			uid = self._uid_from_session( s )
		)

		self._set_times( parent, s, None )

		# extract parts
		parts = [ self._from_single_exercise( s, p, force_sid=False ) for p in el ]

		# update members
		parent.metadata.parts = [ p.uid for p in parts ]
		[ p.metadata.part_of.append( parent.uid ) for p in parts ]

		# assume the parts are already sorted by starttime
		parent.gaps = [ p2.endtime - p1.starttime for p1, p2 in pairwise( parts ) ]

		return parent, tuple( parts )

	@staticmethod
	def _set_times( a: Activity, s: TrainingSession, e: Optional[Exercise] ) -> None:
		# timezone = get_timezone().zone

		start = e.startTime if e and e.startTime else s.startTime
		end = e.stopTime if e and e.stopTime else s.stopTime

		# offset might be empty in some exercises -> use session instead
		offset = e.timezoneOffsetMinutes if e and e.timezoneOffsetMinutes else s.timezoneOffsetMinutes
		if offset is None:
			# both timezoneOffsetMinutes values are missing -> that's bad, this happens for very old exercises
			offset = int( to_naive_time( start ).replace( tzinfo=tzlocal() ).utcoffset().seconds / 60 )
			log.warning( f'training session {s.identifier.id} does not contain any timezone information, assuming local timezone with an offset = {offset}' )

		# update start/end times
		a.timezone_offset = offset
		a.starttime = (to_naive_time( start ) - timedelta( minutes=offset )).replace( tzinfo=UTC )
		a.starttime_local = (a.starttime + timedelta( minutes=offset )).replace( tzinfo=tzoffset( None, offset * 60 ) )
		a.endtime = (to_naive_time( end ) - timedelta( minutes=offset )).replace( tzinfo=UTC )
		a.endtime_local = (a.endtime + timedelta( minutes=offset )).replace( tzinfo=tzoffset( None, offset * 60 ) )

	@staticmethod
	def _uid_from_session( s: TrainingSession ) -> UID:
		# todo: will this fail for newer activities?
		return UID( classifier=CLASSIFIER, local_id=int( s.identifier.id ) )

	@staticmethod
	def _uid_from_exercise( s: TrainingSession, e: Exercise, force_sid: bool = False ) -> Tuple[UID, Tuple[str, str]]:
		# sid: prior to 2026-03 a numeric id of the session, a UUID onwards
		# eid: always a numeric id
		# urls in Polar Flow for exercises prior to 2026-03: https://flow.polar.com/training/analysis/<sid>
		# after 2026-03: https://flow.polar.com/training/analysis/<unknown_id> (which does not appear anywhere in takeout data)

		sid, eid = s.identifier.id, e.identifier.id
		if sid.isdigit():
			# unfortunately need to differentiate for historic reasons:
			# sid was used as uid, although eid would have been the better choice
			# drawback: is not possible to calculate the Flow URL from eid
			# force_sid = True is used for single exercises
			# force_sid = False is used for exercises which are part of multipart
			if force_sid:
				return UID( classifier=CLASSIFIER, local_id=int( sid ) ), ( 'exercise_id', str( eid ) )
			else:
				return UID( classifier=CLASSIFIER, local_id=int( eid ) ), ( 'session_id', str( sid ) )
		else:
			# sid is UUID, therefore use eid as uid and store sid in metadata
			# todo: what ids do modern multiparts have?
			return UID( classifier=CLASSIFIER, local_id=int( eid ) ), ( 'session_id', sid )

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

	@staticmethod
	def _gpx_tcx( a: Activity, stream: Stream ) -> Tuple[GPX, TrainingCenterDatabase]:
		# create gpx only if there are locations
		if any( p.lat or p.lon for p in stream.points ):
			gpx = stream.as_gpx()
		else:
			gpx = None

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

from datetime import date, datetime, time as dtime
from re import fullmatch
from typing import List, Literal, Optional, Tuple

from arrow import Arrow, now
from dateutil.tz import UTC

from tracs.core import Keyword, Normalizer, vfield
from tracs.registry import normalizer, Registry
from tracs.rules import DATE_RANGE_PATTERN, FUZZY_DATE_PATTERN, FUZZY_TIME_PATTERN, parse_date_range_as_str, parse_time_range, TIME_RANGE_PATTERN
from tracs.rules import parse_ceil_str, parse_floor_str
from tracs.utils import floor_ceil_from

TIME_FRAMES = Literal[ 'year', 'quarter', 'month', 'week', 'day' ]
YEAR_RANGE = range( 2000, datetime.utcnow().year + 1 )

def floor_ceil( a1: Arrow, a2: Arrow, frame: TIME_FRAMES = 'day' ) -> Tuple[Arrow, Arrow]:
	return a1.floor( frame ), a2.ceil( frame )

def floor_ceil_str( a1: Arrow, a2: Optional[Arrow] = None, frame: TIME_FRAMES = 'day' ) -> Tuple[str, ...]:
	a2 = a1 if a2 is None else a2
	return tuple( f'd"{t.isoformat()}"' for t in floor_ceil( a1, a2, frame ) )

# noinspection PyTypeChecker
Registry.register_keywords(
	# time related keywords
	Keyword( 'morning', 'time between 6:00 and 11:00', 'hour >= 6 and hour < 11' ),
	Keyword( 'noon', 'time between 11:00 and 13:00', 'hour >= 11 and hour < 13' ),
	Keyword( 'afternoon', 'time between 13:00 and 18:00', 'hour >= 13 and hour < 18' ),
	Keyword( 'evening', 'time between 18:00 and 22:00', 'hour >= 18 and hour < 22' ),
	Keyword( 'night', 'time between 22:00 and 6:00', 'hour >= 22 or hour < 6' ),
	# date related keywords
	Keyword( 'last7days', 'date is within the last 7 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-6 ), now() ) ) ),
	Keyword( 'last14days', 'date is within the last 14 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-13 ), now() ) ) ),
	Keyword( 'last30days', 'date is within the last 30 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-29 ), now() ) ) ),
	Keyword( 'last60days', 'date is within the last 60 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-59 ), now() ) ) ),
	Keyword( 'last90days', 'date is within the last 90 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-89 ), now() ) ) ),
	Keyword( 'yesterday', 'date is yesterday', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-1 ), None, 'day' ) ) ),
	Keyword( 'today', 'date is today', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), None, 'day' ) ) ),
	Keyword( 'lastweek', 'date is within last week', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( weeks=-1 ), None, 'week' ) ) ),
	Keyword( 'thisweek', 'date is within the current week', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), None, 'week' ) ) ),
	Keyword( 'lastmonth', 'date is within last month', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( months=-1 ), None, 'month' ) ) ),
	Keyword( 'thismonth', 'date is within the current month', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), None, 'month' ) ) ),
	Keyword( 'lastquarter', 'month of date is within last quarter', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( months=-3 ), None, 'quarter' ) ) ),
	Keyword( 'thisquarter', 'month of date is within the current quarter', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), None, 'quarter' ) ) ),
	Keyword( 'lastyear', 'year of date is last year', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( years=-1 ), None, 'year' ) ) ),
	Keyword( 'thisyear', 'year of date is current year', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), None, 'year' ) ) ),
)

# normalizers transform a field/value pair into a valid normalized expression
# this enables operations like 'list classifier:polar' where ':' does not evaluate to '=='
# the normalizer is called like function( left, operator, right, normalized_rule )
Registry.register_normalizer(
	Normalizer( 'classifier', str, 'tests if a provided classifier is contained in the list of classifiers of an activity', lambda l, o, r, nr: f'"{r}" in classifiers' ),
	Normalizer( 'service', str, 'alias for classifier', lambda l, o, r, nr: f'"{r}" in classifiers' ),
	Normalizer( 'source', str, 'alias for classifier', lambda l, o, r, nr: f'"{r}" in classifiers' ),
	Normalizer( 'type', str, 'normalizer to support filtering for type names', lambda l, o, r, nr: f'type.name == "{r.lower()}"' ),
)

@normalizer( type=int, description='treat ids from 2000 to current year as years rather than ids' )
def id( left, op, right, rule ) -> str:
	try:
		return f'year == {right}' if int( right ) in YEAR_RANGE else rule
	except (TypeError, ValueError):
		return rule

@normalizer( type=datetime, description='allow access to localtime via provided date string' )
def date( left, op, right, rule ) -> str:
	if fullmatch( FUZZY_DATE_PATTERN, right ):
		return 'localtime >= d"{}" and localtime <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
	elif DATE_RANGE_PATTERN.fullmatch( right ):
		return 'localtime >= d"{}" and localtime <= d"{}"'.format( *parse_date_range_as_str( right ) )
	else:
		return rule

@normalizer( type=datetime, description='allow access to localtime via provided time string' )
def time( left, op, right, rule ) -> str:
	if fullmatch( FUZZY_TIME_PATTERN, right ):
		return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
	elif TIME_RANGE_PATTERN.fullmatch( right ):
		return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *parse_time_range( right, as_str=True ) )
	else:
		return rule

Registry.register_virtual_field(
	vfield( 'classifiers', List[str], lambda a: list( map( lambda s: s.split( ':', 1 )[0], a.uids ) ), 'Classifiers', 'list of classifiers of an activity' ),
	# date/time fields
	vfield( 'weekday', int, lambda a: a.localtime.year, 'Weekday', 'day of week at which the activity has taken place (as number)' ),
	vfield( 'hour', int, lambda a: a.localtime.hour, 'Hour of Day', 'hour in which the activity has been started' ),
	vfield( 'day', int, lambda a: a.localtime.day, 'Day of Month', 'day on which the activity has taken place' ),
	vfield( 'month', int, lambda a: a.localtime.month, 'Month', 'month in which the activity has taken place' ),
	vfield( 'year', int, lambda a: a.localtime.year, 'Year', 'year in which the activity has taken place' ),
	# time helper
	vfield( '__time__', datetime, lambda a: datetime( 1, 1, 1, a.localtime.hour, a.localtime.minute, a.localtime.second, tzinfo=UTC ), 'Helper for time calculations', 'local time without a date and tz' ),
)

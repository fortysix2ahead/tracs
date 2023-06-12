from datetime import date
from typing import List, Literal, Tuple

from arrow import Arrow, now

from tracs.core import Keyword, Normalizer, vfield
from tracs.registry import Registry

TIME_FRAMES = Literal[ 'year', 'quarter', 'month', 'week', 'day' ]

def floor_ceil( a: Arrow, frame: TIME_FRAMES ) -> Tuple[Arrow, Arrow]:
	return a.floor( frame ), a.ceil( frame )

def floor_ceil_str( a: Arrow, frame: TIME_FRAMES ) -> Tuple[str, ...]:
	return tuple( f'd"{t.isoformat()}"' for t in floor_ceil( a, frame ) )

# noinspection PyTypeChecker
Registry.register_keywords(
	# time related keywords
	Keyword( 'morning', 'time between 6:00 and 11:00', 'hour >= 6 and hour < 11' ),
	Keyword( 'noon', 'time between 11:00 and 13:00', 'hour >= 11 and hour < 13' ),
	Keyword( 'afternoon', 'time between 13:00 and 18:00', 'hour >= 13 and hour < 18' ),
	Keyword( 'evening', 'time between 18:00 and 22:00', 'hour >= 18 and hour < 22' ),
	Keyword( 'night', 'time between 22:00 and 6:00', 'hour >= 22 or hour < 6' ),
	# date related keywords
	Keyword( 'last7days', 'date is within the last 7 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-6 ), 'day' ) ) ),
	Keyword( 'last14days', 'date is within the last 14 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-13 ), 'day' ) ) ),
	Keyword( 'last30days', 'date is within the last 30 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-29 ), 'day' ) ) ),
	Keyword( 'last60days', 'date is within the last 60 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-59 ), 'day' ) ) ),
	Keyword( 'last90days', 'date is within the last 90 days', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-89 ), 'day' ) ) ),
	Keyword( 'yesterday', 'date is yesterday', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( days=-1 ), 'day' ) ) ),
	Keyword( 'today', 'date is today', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), 'day' ) ) ),
	Keyword( 'lastweek', 'date is within last week', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( weeks=-1 ), 'week' ) ) ),
	Keyword( 'thisweek', 'date is within the current week', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), 'week' ) ) ),
	Keyword( 'lastmonth', 'date is within last month', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( months=-1 ), 'month' ) ) ),
	Keyword( 'thismonth', 'date is within the current month', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), 'month' ) ) ),
	Keyword( 'lastquarter', 'month of date is within last quarter', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( months=-3 ), 'quarter' ) ) ),
	Keyword( 'thisquarter', 'month of date is within the current quarter', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), 'quarter' ) ) ),
	Keyword( 'lastyear', 'year of date is last year', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now().shift( years=-1 ), 'year' ) ) ),
	Keyword( 'thisyear', 'year of date is current year', lambda: 'time >= {} and time <= {}'.format( *floor_ceil_str( now(), 'year' ) ) ),
)

# normalizers transform a field/value pair into a valid normalized expression
# this enables operations like 'list classifier:polar' where ':' does not evaluate to '=='
Registry.register_normalizer(
	Normalizer( 'classifier', 'tests if a provided classifier is contained in the list of classifiers of an activity', lambda v: f'"{v}" in classifiers' ),
	Normalizer( 'service', 'alias for classifier', lambda v: f'"{v}" in classifiers' ),
	Normalizer( 'source', 'alias for classifier', lambda v: f'"{v}" in classifiers' ),
)

Registry.register_virtual_field(
	vfield( 'classifiers', List[str], lambda a: list( map( lambda s: s.split( ':', 1 )[0], a.uids ) ), 'Classifiers', 'list of classifiers of an activity' ),
	# date/time fields
	vfield( 'weekday', int, lambda a: a.localtime.year, 'Weekday', 'day of week at which the activity has taken place (as number)' ),
	vfield( 'hour', int, lambda a: a.localtime.hour, 'Hour of Day', 'hour in which the activity has been started' ),
	vfield( 'day', int, lambda a: a.localtime.day, 'Day of Month', 'day on which the activity has taken place' ),
	vfield( 'month', int, lambda a: a.localtime.month, 'Month', 'month in which the activity has taken place' ),
	vfield( 'year', int, lambda a: a.localtime.year, 'Year', 'year in which the activity has taken place' ),
	# time as date
	vfield( 'date', date, lambda a: a.localtime.date(), 'Date', 'date of activity' ),

)

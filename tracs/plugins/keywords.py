from datetime import datetime
from typing import Literal, Optional, Tuple

from arrow import Arrow, now
from dateutil.tz import UTC

from tracs.core import Keyword
from tracs.pluginmgr import keyword

TIME_FRAMES = Literal[ 'year', 'quarter', 'month', 'week', 'day' ]
YEAR_RANGE = range( 2000, datetime.now( UTC ).year + 1 )
WITHIN_STARTTIME_LOCAL = 'starttime_local >= {} and starttime_local <= {}'

def floor_ceil( a1: Arrow, a2: Arrow, frame: TIME_FRAMES = 'day' ) -> Tuple[Arrow, Arrow]:
	return a1.floor( frame ), a2.ceil( frame )

def floor_ceil_str( a1: Arrow, a2: Optional[Arrow] = None, frame: TIME_FRAMES = 'day' ) -> Tuple[str, ...]:
	a2 = a1 if a2 is None else a2
	return tuple( f'd"{t.isoformat()}"' for t in floor_ceil( a1, a2, frame ) )

# static keywords for periods of day

@keyword
def morning() -> Keyword:
	return Keyword( 'morning', 'time between 6:00 and 11:00', 'hour >= 6 and hour < 11' )

@keyword
def noon() -> Keyword:
	return Keyword( 'noon', 'time between 11:00 and 13:00', 'hour >= 11 and hour < 13' )

@keyword
def afternoon() -> Keyword:
	return Keyword( 'afternoon', 'time between 13:00 and 18:00', 'hour >= 13 and hour < 18' )

@keyword
def evening() -> Keyword:
	return Keyword( 'evening', 'time between 18:00 and 22:00', 'hour >= 18 and hour < 22' )

@keyword
def night() -> Keyword:
	return Keyword( 'night', 'time between 22:00 and 6:00', 'hour >= 22 or hour < 6' )

# keywords for 'within last X days'

@keyword
def last7days() -> Keyword:
	return Keyword( 'last7days', 'date is within the last 7 days', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-6 ), now() ) ) )

@keyword
def last14days() -> Keyword:
	return Keyword( 'last14days', 'date is within the last 14 days', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-13 ), now() ) ) )

@keyword
def last30days() -> Keyword:
	return Keyword( 'last30days', 'date is within the last 30 days', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-29 ), now() ) ) )

@keyword
def last60days() -> Keyword:
	return Keyword( 'last60days', 'date is within the last 60 days', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-59 ), now() ) ) )

@keyword
def last90days() -> Keyword:
	return Keyword( 'last90days', 'date is within the last 90 days', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-89 ), now() ) ) )

# keywords for days

@keyword
def today() -> Keyword:
	return Keyword( 'today', 'date is today', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now(), None, 'day' ) ) )

@keyword
def yesterday() -> Keyword:
	return Keyword( 'yesterday', 'date is yesterday', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( days=-1 ), None, 'day' ) ) )

# keywords for weeks

@keyword
def thisweek() -> Keyword:
	return Keyword( 'thisweek', 'date is within current week', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now(), None, 'week' ) ) )

@keyword
def lastweek() -> Keyword:
	return Keyword( 'lastweek', 'date is within last week', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( weeks=-1 ), None, 'week' ) ) )

# keywords for months

@keyword
def thismonth() -> Keyword:
	return Keyword( 'thismonth', 'date is within current month', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now(), None, 'month' ) ) )

@keyword
def lastmonth() -> Keyword:
	return Keyword( 'lastmonth', 'date is within last month', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( months=-1 ), None, 'month' ) ) )

# keywords for quarters

@keyword
def thisquarter() -> Keyword:
	return Keyword( 'thisquarter', 'date is within current quarter', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now(), None, 'quarter' ) ) )

@keyword
def lastquarter() -> Keyword:
	return Keyword( 'lastquarter', 'date is within last quarter', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( months=-3 ), None, 'quarter' ) ) )

# keywords for years

@keyword
def thisyear() -> Keyword:
	return Keyword( 'thisyear', 'date is within current year', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now(), None, 'year' ) ) )

@keyword
def lastyear() -> Keyword:
	return Keyword( 'lastyear', 'date is within last year', WITHIN_STARTTIME_LOCAL.format( *floor_ceil_str( now().shift( years=-1 ), None, 'year' ) ) )

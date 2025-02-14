from datetime import datetime
from re import fullmatch
from typing import Literal, Optional, Tuple

from arrow import Arrow, now

from tracs.core import Keyword, Normalizer
from tracs.pluginmgr import keyword, normalizer
from tracs.rules import DATE_RANGE_PATTERN, FUZZY_DATE_PATTERN, FUZZY_TIME_PATTERN, parse_date_range_as_str, parse_time_range, TIME_RANGE_PATTERN
from tracs.utils import floor_ceil_from

TIME_FRAMES = Literal[ 'year', 'quarter', 'month', 'week', 'day' ]
YEAR_RANGE = range( 2000, datetime.utcnow().year + 1 )

WITHIN_STARTTIME_LOCAL = 'starttime_local >= {} and starttime_local <= {}'

def floor_ceil( a1: Arrow, a2: Arrow, frame: TIME_FRAMES = 'day' ) -> Tuple[Arrow, Arrow]:
	return a1.floor( frame ), a2.ceil( frame )

def floor_ceil_str( a1: Arrow, a2: Optional[Arrow] = None, frame: TIME_FRAMES = 'day' ) -> Tuple[str, ...]:
	a2 = a1 if a2 is None else a2
	return tuple( f'd"{t.isoformat()}"' for t in floor_ceil( a1, a2, frame ) )

# normalizers transform a field/value pair into a valid normalized expression
# this enables operations like 'list classifier:polar' where ':' does not evaluate to '=='
# the normalizer is called like function( left, operator, right, normalized_rule )

@normalizer
def classifier() -> Normalizer:
	return Normalizer( 'classifier', str, 'tests if a provided classifier is contained in the list of classifiers of an activity', lambda l, o, r, nr: f'"{r}" in classifiers' )

@normalizer
def service() -> Normalizer:
	return Normalizer( 'service', str, 'alias for classifier', lambda l, o, r, nr: f'"{r}" in classifiers' )

@normalizer
def source() -> Normalizer:
	return Normalizer( 'source', str, 'alias for classifier', lambda l, o, r, nr: f'"{r}" in classifiers' )

@normalizer
def type() -> Normalizer:
	return Normalizer( 'type', str, 'normalizer to support filtering for type names', lambda l, o, r, nr: f'type.name == "{r.lower()}"' )

@normalizer( type=int, description='treat ids from 2000 to current year as years rather than ids' )
def id( left, op, right, rule ) -> str:
	try:
		return f'year == {right}' if int( right ) in YEAR_RANGE else rule
	except (TypeError, ValueError):
		return rule

@normalizer( type=datetime, description='allow access to date via provided date string' )
def date( left, op, right, rule ) -> str:
	if fullmatch( FUZZY_DATE_PATTERN, right ):
		return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
	elif DATE_RANGE_PATTERN.fullmatch( right ):
		return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *parse_date_range_as_str( right ) )
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

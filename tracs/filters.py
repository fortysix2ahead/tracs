
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as fld
from datetime import date
from datetime import datetime
from datetime import time
from enum import Enum
from logging import getLogger
from numbers import Number
from re import IGNORECASE
from re import match
from sys import float_info
from typing import Any
from typing import Callable
from typing import cast
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from arrow import Arrow
from arrow import now
from dateutil.tz import UTC
from tinydb.queries import Query
from tinydb.queries import QueryLike

from .config import CLASSIFIER as FIELD_CLASSIFIER
from .config import CLASSIFIERS as FIELD_CLASSIFIERS
from .plugins import Registry

log = getLogger( __name__ )

CLASSIFIER_FIELDS = [FIELD_CLASSIFIER, 'service', 'source']

NEGATE = '(?P<negate>^)'
FIELD = '(?P<field>\w+)'
SERVICE = '((?P<service>\w+)\.)?'
CLASSIFIER = '((?P<classifier>\w+)\.)?'

INTEGER = '(?P<value>\d+)'
PLAIN_INTEGER = '(\d+)'
INTEGER_RANGE = '(?P<range_from>\d+)?\.\.(?P<range_to>\d+)?'

FLOAT = '(?P<value>\d+\.\d+)'
PLAIN_FLOAT = '(\d+\.\d+)'
FLOAT_RANGE = '(?P<range_from>\d+\.\d+)?\.\.(?P<range_to>\d+\.\d+)?'

NUMBER = '(?P<value>\d+(\.\d+)?)'
PLAIN_NUMBER = '(\d+(\.\d+)?)'

DATE = '(?P<year>\d\d\d\d)(-(?P<month>\d\d))?(-(?P<day>\d\d))?'
DATE_FROM = '(?P<year_from>\d\d\d\d)(-(?P<month_from>\d\d))?(-(?P<day_from>\d\d))?'
DATE_TO = '(?P<year_to>\d\d\d\d)(-(?P<month_to>\d\d))?(-(?P<day_to>\d\d))?'

TIME = '(?P<hour>\d\d)(:(?P<minute>\d\d))?(:(?P<second>\d\d))?'
TIME_FROM = '(?P<hour_from>\d\d)(:(?P<minute_from>\d\d))?(:(?P<second_from>\d\d))?'
TIME_TO = '(?P<hour_to>\d\d)(:(?P<minute_to>\d\d))?(:(?P<second_to>\d\d))?'

WORD = '(?P<value>\w+)'
PLAIN_WORD = '([a-zA-Z]\w*)'
EXPR = '(?P<expr>.+)$'

#R_FIELD_EXPR = '{SERVICE}{FIELD}:{EXPR}'.format( SERVICE = SERVICE, FIELD = FIELD, EXPR = EXPR )
#R_FIELD_EMPTY_EXPR = '{SERVICE}{FIELD}:'.format( SERVICE = SERVICE, FIELD = FIELD )

R_FIELD_EXPR = '{FIELD}:{EXPR}'.format( FIELD=FIELD, EXPR=EXPR )
R_FIELD_EMPTY_EXPR = '{FIELD}:'.format( FIELD=FIELD )

R_CLASSIFIER_FIELD_EXPR = '{CLASSIFIER}{FIELD}:{EXPR}'.format( CLASSIFIER = CLASSIFIER, FIELD = FIELD, EXPR = EXPR )
R_CLASSIFIER_FIELD_EMPTY_EXPR = '{CLASSIFIER}{FIELD}:'.format( CLASSIFIER = CLASSIFIER, FIELD = FIELD )

R_EXPR_INTEGER = '{INTEGER}$'.format( INTEGER = INTEGER )
R_EXPR_INTEGER_RANGE = '{INTEGER_RANGE}$'.format( INTEGER_RANGE = INTEGER_RANGE )
R_EXPR_INTEGER_SEQUENCE = '^({INTEGER})(,{INTEGER})*$'.format( INTEGER = PLAIN_INTEGER )

R_EXPR_FLOAT = '{FLOAT}$'.format( FLOAT = FLOAT )
R_EXPR_FLOAT_RANGE = '{FLOAT_RANGE}$'.format( FLOAT_RANGE = FLOAT_RANGE )
R_EXPR_FLOAT_SEQUENCE = '^({FLOAT})(,{FLOAT})*$'.format( FLOAT = PLAIN_FLOAT )

R_EXPR_WORD = '{WORD}$'.format( WORD = WORD )
R_EXPR_WORD_SEQUENCE = '^({WORD})(,{WORD})*$'.format( WORD = PLAIN_WORD )
#R_EXPR_WORD_SEQUENCE = '((?:^|[,])\w+)+'
#R_EXPR_WORD_SEQUENCE = '[^,\s][^\,]*[^,\s]*'

R_EXPR_DATE = '{DATE}$'.format( DATE = DATE )
R_EXPR_DATE_RANGE = '({DATE_FROM})?\.\.({DATE_TO})?$'.format( DATE_FROM = DATE_FROM, DATE_TO = DATE_TO )

R_EXPR_TIME = '{TIME}$'.format( TIME = TIME )
R_EXPR_TIME_RANGE = '({TIME_FROM})?\.\.({TIME_TO})?$'.format( TIME_FROM = TIME_FROM, TIME_TO = TIME_TO )

@dataclass
class Filter( QueryLike ):

	field: Optional[Union[str, List[str]]] = fld( default=None ) # field to filter for

	# value which needs to match, example: calories = 100 matches doc['calories] = 100
	# if value is a list: example: location = [Berlin, Frankfurt, Hamburg] matches doc[location] = Berlin
	value: Any = fld( default=None )
	# classifier: Optional[str] = fld( default=None )
	# sequence: Optional[List] = fld( default=None )
	range_from: Any = fld( default=None )
	range_to: Any = fld( default=None )

	regex: bool = fld( default=True ) # indicator that value does not contain the exact value to match but a regex instead
	part_of_list: bool = fld( default=False ) # when true the value is expected to be part of a list
	negate: bool = fld( default=False )

	# callable to be executed during filter evaluation
	callable: Optional[Union[Callable, QueryLike]] = fld( default=None, repr=False, compare=False )
	valid: bool = fld( default=True, repr=False, compare=False )

	def __post_init__( self ):
		self.freeze()

	def __call__( self, value: Mapping ) -> bool:
		if self.callable:
			return self.callable( value )
		else:
			raise RuntimeError( f'error calling filter {self}, has the filter been freezed?' )

	# noinspection PyTypeChecker
	def freeze( self ) -> Filter:
		"""
		Freezes this filter (sets up the right callable for execution based on the filter fields) and returns self for convenience.

		:return: self
		"""
		if self.callable:
			return # do nothing if a callable already exists

		if not self.valid:
			self.callable = invalid() # create invalid callable if flag valid is false
			return

		if self.field is None:
			if type( self.value ) is int:
				self.callable = (Query()['id'] == self.value) | (Query()['raw_id'] == self.value)

		if type( self.field ) is str:
			if type( self.value ) is str:
				if self.part_of_list:
					if self.regex:
						self.callable = Query()[self.field].test( lambda values, s: any( [ match( s, v ) for v in values ] ), self.value )
					else:
						self.callable = Query()[self.field].test( lambda values, s: s in values, self.value )
				else:
					if self.regex:
						self.callable = Query()[self.field].matches( self.value, flags=IGNORECASE )
					else:
						self.callable = Query()[self.field] == self.value

			elif isinstance( self.value, Enum ):
				self.callable = Query()[self.field] == self.value

			elif isinstance( self.value, Number ):
				self.callable = Query()[self.field] == self.value

			elif isinstance( self.value, datetime ):
				pass

			elif isinstance( self.value, time ):
				def fn( value: Union[datetime, time], _tm: time ) -> bool:
					value = value.time() if type( value ) is datetime else value
					return True if value == _tm else False
				self.callable = Query()[self.field].test( fn, self.value )

			elif isinstance( self.value, list ):
				self.callable = Query()[self.field].one_of( self.value )

			elif isinstance( self.range_from, Number ) or isinstance( self.range_to, Number ):
				def fn( value: Number, _from: Number, _to: Number ) -> bool:
					if value and _from <= value < _to:
						return True
					return False
				_from = self.range_from if self.range_from else float_info.min
				_to = self.range_to if self.range_to else float_info.max
				# self.callable = (Query()[self.field] >= _from) & (Query()[self.field] < _to) # this fails if field value is None
				self.callable = Query()[self.field].test( fn, _from, _to )

			elif isinstance( self.range_from, datetime ) or isinstance( self.range_to, datetime ):
				def fn( value: datetime, _from: datetime, _to: datetime ) -> bool:
					return True if value and _from <= value <= _to else False
				from_time = self.range_from.astimezone( UTC ) if self.range_from else datetime( 1900, 1, 1, tzinfo=UTC )
				to_time = self.range_to.astimezone( UTC ) if self.range_to else datetime( 2100, 1, 1, tzinfo=UTC )
				self.callable = Query()[self.field].test( fn, from_time, to_time )

			elif isinstance( self.range_from, time ) or isinstance( self.range_to, time ):
				def fn( value: Union[datetime, time], _from_time: time, _to_time: time ) -> bool:
					value = value.time() if type( value ) is datetime else value
					if _from_time <= value < _to_time:
						return True
					return False
				from_time = self.range_from if self.range_from else time( 0, 0, 0, 0 )
				to_time = self.range_to if self.range_to else time( 23, 59, 59, 999999 )
				self.callable = Query()[self.field].test( fn, from_time, to_time )

			elif self.value is None:
				self.callable = Query()[self.field].test( lambda v: True if v else False )

			else:
				self.valid = False
				self.callable = invalid()

		if self.valid and self.negate:
			self.callable = ~ cast( Query, self.callable )

		return self

	def is_empty( self ) -> bool:
		if not self.value and not self.sequence and not self.range_from and not self.range_to:
			return True
		else:
			return False

@dataclass
class FilterGroup( QueryLike ):

	AND: str = 'AND'
	OR: str = 'OR'

	filters: List[Filter] = fld( default=None )
	conjunction: str = fld( default=AND )

# prepared/predefined filters

def false() -> Filter:
	return Filter( field=None, value=False, callable=lambda m: False )

def true() -> Filter:
	return Filter( field=None, value=True, callable=lambda m: True )

def invalid() -> Filter:
	# noinspection PyUnusedLocal
	def fn( value: Mapping ) -> bool:
		raise RuntimeError( f'unable to execute a query marked as invalid' )
	return Filter( field=None, value=False, callable=fn, valid=False )

def classifier( c: str ) -> Filter:
	return Filter( 'uids', f'^{c}:\d+$', regex=True, part_of_list=True )

def raw_id( id: int ) -> Filter:
	return Filter( 'uids', f'^\w+:{id}+$', regex=True, part_of_list=True )

def uid( uid: str ) -> Filter:
	return Filter( 'uids', uid, regex=False, part_of_list=True )

def is_number( field: str ) -> Filter:
	return Filter( field, callable=lambda v: isinstance( v.get( field ), ( float, int ) ) )

# parse functions

def parse_filters( filters: Union[List[Filter, str], Filter, str] ) -> [Filter]:
	"""
	Parses a list of strings into a list of filters.

	:param filters: list of string to be parsed.
	:return: list of parsed filters
	"""
	if not filters:
		return []
	elif type( filters ) is str:
		return [ parse( filters ) ]
	elif type( filters ) is Filter:
		return [ filters ]
	else:
		return [ parse( f ) for f in filters ]

def parse( filter: Union[Filter, str] ) -> Optional[Filter]:
	"""
	Parses a string into a valid filter. The filter might already be usable, but there's no guarantee. In order to make
	the filter usable, call prepare( f ).

	:param filter: string to be parsed into a filter
	:return: parsed filter
	"""
	if not len( filter ) > 0:
		return Filter.true()

	if type( filter ) is Filter:
		return filter

	# create empty filter
	f = Filter()

	# filter is negated?
	filter, f.negate = (filter[1:], True) if filter[0] == '^' else (filter, False)

	expr = ''

	# integer number -> treat as id
	if m:= match( INTEGER, filter ):
		f.field = 'id'
		f.value = int( m.groupdict()['value'] )

#	if m:= match( STRING, filter ):
#		f.field = 'name'
#		f.value = m.groupdict()['value']
#		f.exact = False

	# field:expression
	elif m := match( R_FIELD_EXPR, filter ):
		f.field = m.groupdict()['field']
		expr = m.groupdict()['expr']

	elif m := match( R_FIELD_EMPTY_EXPR, filter ):
		f.field = m.groupdict()['field']

	if expr:
		if me := match( R_EXPR_INTEGER, expr ):
			f.value = int( me.groupdict()['value'] )

		elif me := match( R_EXPR_FLOAT, expr ):
			f.value = float( me.groupdict()['value'] )

		elif me := match( R_EXPR_WORD, expr ):
			f.value = me.groupdict()['value']

		elif me := match( R_EXPR_INTEGER_SEQUENCE, expr ):
			f.value = [int( i ) for i in me.group().split( ',' )]

		elif me := match( R_EXPR_FLOAT_SEQUENCE, expr ):
			f.value = [float( i ) for i in me.group().split( ',' )]

		elif me := match( R_EXPR_WORD_SEQUENCE, expr ):
			f.value = [i for i in me.group().split( ',' )]

		elif me := match( R_EXPR_INTEGER_RANGE, expr ):
			if me.groupdict()['range_from']:
				f.range_from = int( me.groupdict()['range_from'] )
			if me.groupdict()['range_to']:
				f.range_to = int( me.groupdict()['range_to'] )

		elif me := match( R_EXPR_FLOAT_RANGE, expr ):
			if me.groupdict()['range_from']:
				f.range_from = float( me.groupdict()['range_from'] )
			if me.groupdict()['range_to']:
				f.range_to = float( me.groupdict()['range_to'] )

		elif me := match( R_EXPR_DATE, expr ):
			year = int( me.groupdict()['year'] )
			month = int( me.groupdict()['month'] )
			if me.groupdict()['day']:
				f.range_from = _floor( year, month, int( me.groupdict()['day'] ) )
				f.range_to = _ceil( year, month, int( me.groupdict()['day'] ) )
			else:
				f.range_from = _floor( year, month )
				f.range_to = _ceil( year, month )

		elif me := match( R_EXPR_DATE_RANGE, expr ):
			hour_from = me.groupdict()['year_from']
			minute_from = me.groupdict()['month_from']
			second_from = me.groupdict()['day_from']
			if me.groupdict()['day_from']:
				f.range_from = _floor( int( hour_from ), int( minute_from ), int( second_from ) )
			elif me.groupdict()['month_from']:
				f.range_from = _floor( int( hour_from ), int( minute_from ) )
			elif me.groupdict()['year_from']:
				f.range_from = _floor( int( hour_from ) )

			hour_to = me.groupdict()['year_to']
			month_to = me.groupdict()['month_to']
			day_to = me.groupdict()['day_to']
			if me.groupdict()['day_to']:
				f.range_to = _ceil( int( hour_to ), int( month_to ), int( day_to ) )
			elif me.groupdict()['month_to']:
				f.range_to = _ceil( int( hour_to ), int( month_to ) )
			elif me.groupdict()['year_to']:
				f.range_to = _ceil( int( hour_to ) )

		elif me := match( R_EXPR_TIME, expr ):
			hour = int( me.groupdict()['hour'] )
			if me.groupdict()['second']:
				f.value= time( hour, int( me.groupdict()['minute'] ), int( me.groupdict()['second'] ) )
			elif me.groupdict()['minute']:
				f.value = time( hour, int( me.groupdict()['minute'] ) )
			else:
				f.value= time( hour )

		elif me := match( R_EXPR_TIME_RANGE, expr ):
			hour_from = me.groupdict()['hour_from']
			minute_from = me.groupdict()['minute_from']
			second_from = me.groupdict()['second_from']
			if me.groupdict()['second_from']:
				f.range_from = time( int( hour_from ), int( minute_from ), int( second_from ) )
			elif me.groupdict()['minute_from']:
				f.range_from = time( int( hour_from ), int( minute_from ) )
			elif me.groupdict()['hour_from']:
				f.range_from = time( int( hour_from ) )

			hour_to = me.groupdict()['hour_to']
			minute_to = me.groupdict()['minute_to']
			second_to = me.groupdict()['second_to']
			if me.groupdict()['second_to']:
				f.range_to = time( int( hour_to ), int( minute_to ), int( second_to ) )
			elif me.groupdict()['minute_to']:
				f.range_to = time( int( hour_to ), int( minute_to ) )
			elif me.groupdict()['hour_to']:
				f.range_to = time( int( hour_to ) )

	# prepare the filter (adjustments after parsing)

	# special treatment of raw ids
	if f.field in Registry.services.keys() and type( f.value ) is int:
		f.value = f'{f.field}:{f.value}'
		f.field = 'uids'
		f.regex = False

	if f.field in ['classifier', 'service', 'source'] and f.value in Registry.services.keys():
		f.field = 'uids'
		f.value = f'^{f.value}:.*$'
		f.regex = True
		f.part_of_list = True

	# date:<year> is captured by <field>:<int> in parser, so we need to correct it here
	# same holds true for date:<year>..<year>
	if f.field == 'date':
		if isinstance( f.value, int ):
			f.range_from, f.range_to = _floor( f.value ), _ceil( f.value )
		if f.range_from and isinstance( f.range_from, int ):
			f.range_from = _floor( f.range_from )
		if f.range_to and isinstance( f.range_to, int ):
			f.range_to = _ceil( f.range_to )
		if isinstance( f.value, str ):
			f.range_from, f.range_to = _range_of_keyword( keyword=f.value )
		f.field = 'time' # adjustment: we are not querying the date field, but the time field
		f.value = None

	if f.field == 'time':
		if isinstance( f.value, int ):
			f.value = time( f.value )
		elif isinstance( f.value, str ):
			if f.value == 'morning':
				f.range_from, f.range_to = time( 6 ), time( 11 )
			elif f.value == 'noon':
				f.range_from, f.range_to = time( 11 ), time( 13 )
			elif f.value == 'afternoon':
				f.range_from, f.range_to = time( 13 ), time( 18 )
			elif f.value == 'evening':
				f.range_from, f.range_to = time( 18 ), time( 22 )
			elif f.value == 'night':
				f.range_from, f.range_to = time( 22 ), time( 6 )
			f.value = None

		if isinstance( f.range_from, int ):
			f.range_from = time( f.range_from )
		elif isinstance( f.range_from, str ):
			f.range_from = time.fromisoformat( f.range_from )
		if isinstance( f.range_to, int ):
			f.range_to = time( f.range_to )

	# finally freeze the filter
	return f.freeze()

# helper functions

def _floor( year = None, month = None, day = None ) -> Optional[datetime]:
	if day:
		return Arrow( year, month, day ).floor( 'day' ).datetime
	elif month:
		return Arrow( year, month, 15 ).floor( 'month' ).datetime
	elif year:
		return Arrow( year, 7, 15 ).floor( 'year' ).datetime
	else:
		return None

def _ceil( year = None, month = None, day = None ) -> Optional[datetime]:
	if day:
		return Arrow( year, month, day ).ceil( 'day' ).datetime
	elif month:
		return Arrow( year, month, 15 ).ceil( 'month' ).datetime
	elif year:
		return Arrow( year, 7, 15 ).ceil( 'year' ).datetime
	else:
		return None

def _range_of_keyword( keyword ) -> (Optional[date], Optional[date]):
	_now = now()
	range_from, range_to = (None, None)
	if keyword == 'today':
		range_from, range_to = _now.floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'thisweek':
		range_from, range_to = _now.floor( 'week' ), _now.ceil( 'week' )
	elif keyword == 'thismonth':
		range_from, range_to = _now.floor( 'month' ), _now.ceil( 'month' )
	elif keyword == 'thisquarter':
		range_from, range_to = _now.floor( 'quarter' ), _now.ceil( 'quarter' )
	elif keyword == 'thisyear':
		range_from, range_to = _now.floor( 'year' ), _now.ceil( 'year' )
	elif keyword == 'yesterday':
		_now = _now.shift( days=-1 )
		range_from, range_to = _now.floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'last7days':
		range_from, range_to = _now.shift( days=-6 ).floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'last30days':
		range_from, range_to = _now.shift( days=-29 ).floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'last60days':
		range_from, range_to = _now.shift( days=-59 ).floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'last90days':
		range_from, range_to = _now.shift( days=-89 ).floor( 'day' ), _now.ceil( 'day' )
	elif keyword == 'lastweek':
		_now = _now.shift( weeks=-1 )
		range_from, range_to = _now.floor( 'week' ), _now.ceil( 'week' )
	elif keyword == 'lastmonth':
		_now = _now.shift( months=-1 )
		range_from, range_to = _now.floor( 'month' ), _now.ceil( 'month' )
	elif keyword == 'lastquarter':
		_now = _now.shift( months=-3 )
		range_from, range_to = _now.floor( 'quarter' ), _now.ceil( 'quarter' )
	elif keyword == 'lastyear':
		_now = _now.shift( years=-1 )
		range_from, range_to = _now.floor( 'year' ), _now.ceil( 'year' )

	return range_from.datetime, range_to.datetime


from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import date
from datetime import datetime
from datetime import time
from enum import Enum
from logging import getLogger
from re import IGNORECASE
from re import match
from sys import float_info
from sys import maxsize
from typing import Any
from typing import Callable
from typing import Tuple
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

from .fields import field_types
from .fields import filter_types
from .plugins import Registry

log = getLogger( __name__ )

# add service names as valid field types
for s in Registry.services.keys():
	filter_types[s] = int

@dataclass
class Filter( QueryLike ):

	# field to filter for
	field: Optional[Union[str, List[str]]] = datafield( default=None )

	# value which needs to match, example: calories = 100 matches doc['calories'] = 100
	value: Any = datafield( default=None )
	# list of values, example: location = [Berlin, Frankfurt, Hamburg] matches doc[location] = Berlin
	values: List[Any] = datafield( default=None )

	# indicate ranges: range_from = 0, range_to = 10 matches doc['calories'] = 5
	range_from: Any = datafield( default=None )
	range_to: Any = datafield( default=None )

	# indicator that value does not contain the exact value to match, but a regular expression
	regex: bool = datafield( default=False )
	# when true value is expected to be part of a list (opposite of 'values' from above)
	value_in_list: bool = datafield( default=False )
	# negates the filter
	negate: bool = datafield( default=False )

	# callable to be executed during filter evaluation
	callable: Optional[Union[Callable, QueryLike]] = datafield( default=None, repr=False, compare=False )
	# indicator that the filter is invalid
	valid: bool = datafield( default=True, repr=False, compare=False )

	def __post_init__( self ):
		self.freeze()

	def __call__( self, value: Mapping ) -> bool:
		if self.callable:
			return self.callable( value )
		else:
			raise RuntimeError( f'error calling filter {self}, has the filter been frozen?' )

	# noinspection PyTypeChecker
	def freeze( self ) -> Filter:
		"""
		Freezes this filter (sets up the right callable for execution based on the filter fields) and returns self for convenience.

		:return: self
		"""
		if self.callable:
			return self# do nothing if a callable already exists

		if not self.valid or self.field not in filter_types:
			self.callable = invalid() # create invalid callable if flag valid is false
			return self

		if field_types.get( self.field ) in [int, float]:
			self._freeze_number()

		elif field_types.get( self.field ) is str:
			self._freeze_str()

		elif field_types.get( self.field ) is Enum:
			self._freeze_enum()

		elif field_types.get( self.field ) == list[str]:
			self._freeze_list()

		elif field_types.get( self.field ) == datetime:
			self._freeze_datetime()

		elif field_types.get( self.field ) == time:
			self._freeze_time()

		elif isinstance( self.value, time ):
			def fn( value: Union[datetime, time], _tm: time ) -> bool:
				value = value.time() if type( value ) is datetime else value
				return True if value == _tm else False
			self.callable = Query()[self.field].test( fn, self.value )

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

	def _freeze_number( self ) -> None:
		if self.value:
			self.callable = Query()[self.field] == self.value
		elif self.values:
			self.callable = Query()[self.field].test( lambda v: True if v in self.values else False )
		elif self.range_from is not None and self.range_to is not None:
			self.callable = Query()[self.field].test( lambda v: True if self.range_from <= v < self.range_to else False )

	def _freeze_str( self ) -> None:
		if self.value:
			if self.regex:
				self.callable = Query()[self.field].matches( self.value, flags=IGNORECASE )
			else:
				self.callable = Query()[self.field].test( lambda v: True if self.value.lower() in v.lower() else False )
		elif self.values:
			pass

#		if self.value_in_list:
#			if self.regex:
#				self.callable = Query()[self.field].test( lambda values, s: any( [match( s, v ) for v in values] ), self.value )
#			else:
#				self.callable = Query()[self.field].test( lambda values, s: s in values, self.value )

	def _freeze_enum( self ) -> None:
		if self.value:
			self.callable = Query()[self.field] == self.value

	def _freeze_list( self ) -> None:
		if self.value:
			self.callable = Query()[self.field].test( lambda v: True if self.value in v else False )

	def _freeze_datetime( self ) -> None:
		if self.value and type( self.value ) is time:
			self.callable = Query()[self.field].test( lambda v: True if v.time() == self.value else False )
		elif self.range_from and self.range_to:
			if type( self.range_from ) is datetime and type( self.range_to ) is datetime:
				range_from = self.range_from.astimezone( UTC )
				range_to = self.range_to.astimezone( UTC )
				self.callable = Query()[self.field].test( lambda v: True if v and range_from <= v <= range_to else False )
			elif type( self.range_from ) is time and type( self.range_to ) is time:
				self.callable = Query()[self.field].test( lambda v: True if v and self.range_from <= v.time() <= self.range_to else False )

	def _freeze_time( self ) -> None:
		pass

	def is_empty( self ) -> bool:
		if not self.value and not self.sequence and not self.range_from and not self.range_to:
			return True
		else:
			return False

@dataclass
class FilterGroup( QueryLike ):

	AND: str = 'AND'
	OR: str = 'OR'

	filters: List[Filter] = datafield( default=None )
	conjunction: str = datafield( default=AND )

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
	return Filter( 'uids', f'^{c}:\d+$', regex=True, value_in_list=True )

def raw_id( id: int ) -> Filter:
	return Filter( 'uids', f'^\w+:{id}+$', regex=True, value_in_list=True )

def uid( uid: str ) -> Filter:
	return Filter( 'uids', uid, regex=False, value_in_list=True )

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


# patterns for parse function

#filter_pattern = '^{negate}{field}{colon}{expr}$'.format( **{
#	'negate': '(?P<negate>\^?)',

filter_pattern = '^{field}{colon}{expr}$'.format( **{
	'field' : '(?P<field>\w+)',
	'colon' : '(?P<colon>::?)',
	'expr'  : '(?P<expr>.*)',
} )

int_pattern = '^(?P<value>\d+)$'
int_list_pattern = '^(?P<values>(\d+,)+(\d+))$'
int_range_pattern = '^(?P<range_from>\d+)?\.\.(?P<range_to>\d+)?$'

number_pattern = '^(?P<value>\d+(\.\d+)?)$'
number_range_pattern = '^(?P<range_from>\d+(\.\d+)?)?\.\.(?P<range_to>\d+(\.\d+)?)?$'

word_pattern = '^(?P<value>[\w-]+)$'
word_quote_pattern = '^"(?P<value>.+)"$'
word_list_pattern = '^(?P<expr>(\w+,)+(\w+))$'

date_pattern = '^(?P<year>[12]\d\d\d)(-(?P<month>[01]\d))?(-(?P<day>[0-3]\d))?$'
date_from_pattern = '((?P<year_from>[12]\d\d\d)(-(?P<month_from>[01]\d))?(-(?P<day_from>[0-3]\d))?)?'
date_to_pattern = '((?P<year_to>[12]\d\d\d)(-(?P<month_to>[01]\d))?(-(?P<day_to>[0-3]\d))?)?'
date_range_pattern = '^{date_from}\.\.{date_to}$'.format( **{
	'date_from': date_from_pattern,
	'date_to': date_to_pattern,
} )
date_range_keyword = '^(?P<value>\w+)$'

time_pattern = '^(?P<hour>[0-1]\d|2[0-4]):?(?P<minute>[0-5]\d)?:?(?P<second>[0-5]\d)?$'
time_from_pattern = '(?P<hour_from>[0-1]\d|2[0-4]):?(?P<minute_from>[0-5]\d)?:?(?P<second_from>[0-5]\d)?'
time_to_pattern = '(?P<hour_to>[0-1]\d|2[0-4]):?(?P<minute_to>[0-5]\d)?:?(?P<second_to>[0-5]\d)?'
time_range_pattern = '^({time_from})?\.\.({time_to})?$'.format( **{
	'time_from': time_from_pattern,
	'time_to': time_to_pattern,
} )
time_range_keyword = '^(?P<value>\w+)$'

range_pattern = '^(?P<range_from>.*)\.\.(?P<range_to>.*)$'
list_pattern = '^(\w+,)+(\w+)$'
simple_pattern = '^(.*)$'

def parse( flt: Union[Filter, str] ) -> Optional[Filter]:
	if type( flt ) is Filter:
		return flt

	# check for negation
	flt, negate = (flt[1:], True) if flt.startswith( '^' ) else (flt, False)

	# preprocess special cases
	flt = preprocess( flt )

	# match filter pattern and parse it
	if m := match( filter_pattern, flt ):
		field, regex, expr = unpack_filter( **m.groupdict() )
		value, values, range_from, range_to, valid = parse_expr( field, expr, regex )
		f = Filter( field=field, value=value, values=values, range_from=range_from, range_to=range_to, valid=valid, negate=negate )
	else: # no match -> set invalid
		f = Filter( valid = False )

	# postprocess parsed filter
	postprocess( f )

	return f.freeze()

def parse_expr( field: str, expr: str, regex: bool ) -> Tuple[Any, Any, Any, Any, bool]:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if field in filter_types:
		field_type = filter_types.get( field )
		if field_type is int:
			value, values, range_from, range_to, valid = parse_int( field, expr )
		elif field_type is float:
			value, values, range_from, range_to, valid = parse_number( field, expr )
		elif field_type is str:
			value, values, range_from, range_to, valid = parse_str( field, expr )
		elif field_type is date:
			value, values, range_from, range_to, valid = parse_date( field, expr )
		elif field_type is time:
			value, values, range_from, range_to, valid = parse_time( field, expr )
		elif field_type is datetime:
			pass  # not yet supported
		elif field_type is Enum:
			value, values, range_from, range_to, valid = parse_enum( field, expr )
		else:
			valid = False

	elif field in Registry.services.keys():
		value, values, range_from, range_to, valid = parse_int( field, expr )
		pass

	else:
		valid = False

	return value, values, range_from, range_to, valid

def parse_int( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( int_pattern, expr ): # single integer
		value = int( m.groupdict().get( 'value' ) )

	elif m := match( int_list_pattern, expr ): # list of integers
		values = list( map( lambda s: int( s ), m.groupdict().get( 'values' ).split( ',' ) ) )

	elif m := match( int_range_pattern, expr ):  # range of integers
		range_from = m.groupdict().get( 'range_from' )
		range_to = m.groupdict().get( 'range_to' )
		if range_from or range_to:
			range_from = int( range_from ) if range_from else ~maxsize
			range_to = int( range_to ) if range_to else maxsize
		else:
			valid = False

	return value, values, range_from, range_to, valid

def parse_number( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( number_pattern, expr ):  # single number
		value = float( m.groupdict().get( 'value' ) )

	elif m := match( number_range_pattern, expr ): # range of numbers
		range_from = m.groupdict().get( 'range_from' )
		range_to = m.groupdict().get( 'range_to' )
		if range_from or range_to:
			range_from = float( range_from ) if range_from else float_info.min
			range_to = float( range_to ) if range_to else float_info.max
		else:
			valid = False

	return value, values, range_from, range_to, valid

def parse_str( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( word_pattern, expr ) or match( word_quote_pattern, expr ): # words, either standalone or quoted
		value = m.groupdict().get( 'value' )

	elif m := match( word_list_pattern, expr ): # word list, quotes are not yet supported
		values = m.groupdict().get( 'expr' ).split( ',' )

	return value, values, range_from, range_to, valid

def parse_enum( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( word_pattern, expr ): # words only
		value = m.groupdict().get( 'value' )

	return value, values, range_from, range_to, valid

def parse_date( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( date_pattern, expr ):
		year, month, day = unpack_date( **m.groupdict() )
		year, month, day = int( year ), int( month ) if month else None, int( day ) if day else None
		range_from, range_to = _floor( year, month, day ), _ceil( year, month, day )

	elif m := match( date_range_pattern, expr ):
		year_from, month_from, day_from, year_to, month_to, day_to = unpack_date_range( **m.groupdict() )
		year_from, month_from, day_from = int( year_from ) if year_from else None, int( month_from ) if month_from else None, int( day_from ) if day_from else None
		year_to, month_to, day_to = int( year_to ) if year_to else None, int( month_to ) if month_to else None, int( day_to ) if day_to else None
		range_from, range_to = _floor( year_from, month_from, day_from ), _ceil( year_to, month_to, day_to )

	elif m := match( date_range_keyword, expr ):
		range_from, range_to = _range_of_date_keyword( m.groupdict().get( 'value' ) )
		if not range_from and not range_to:
			valid = False

	else:
		valid = False

	return value, values, range_from, range_to, valid

def parse_time( field: str, expr: str ) -> Tuple:
	value, values, range_from, range_to, valid = (None, None, None, None, True)

	if m := match( time_pattern, expr ):
		hour, minute, second = unpack_time( **m.groupdict() )
		hour, minute, second = int( hour ), int( minute ) if minute else 0, int( second ) if second else 0
		value = time( hour, minute, second )

	elif m := match( time_range_pattern, expr ):
		hour_from, minute_from, second_from, hour_to, minute_to, second_to = unpack_time_range( **m.groupdict() )
		hour_from, minute_from, second_from = int( hour_from ) if hour_from else 0, int( minute_from ) if minute_from else 0, int( second_from ) if second_from else 0
		hour_to, minute_to, second_to = int( hour_to ) if hour_to else 0, int( minute_to ) if minute_to else 0, int( second_to ) if second_to else 0
		range_from = time( hour_from, minute_from, second_from )
		range_to = time( hour_to, minute_to, second_to )

	elif m := match( time_range_keyword, expr ):
		range_from, range_to = _range_of_time_keyword( m.groupdict().get( 'value' ) )
		if not range_from and not range_to:
			valid = False

	else:
		valid = False

	return value, values, range_from, range_to, valid

def preprocess( flt: str ) -> str:
	# integer number only
	if m := match( int_pattern, flt ):
		flt = f'id:{flt}'

	# list of integers
	elif m := match( int_list_pattern, flt ):
		flt = f'id:{flt}'

	# range of integers
	elif m := match( int_range_pattern, flt ):
		flt = f'id:{flt}'

	return flt

def postprocess( f: Filter ) -> None:

	if not f.valid: # do nothing when filter is already invalid
		return

	if f.field not in filter_types: # mark as invalid when field not in fields
		f.valid = False

	if filter_types[f.field] is str:
		postprocess_string( f )

	elif filter_types[f.field] is date:
		postprocess_date( f )

	if f.field in Registry.services.keys() and type( f.value ) is int:  # allow queries like <service>:<id>
		f.value = f'{f.field}:{f.value}'
		f.field = 'uids'

	if f.field == 'service' or f.field == 'source': # allow service/source queries
		f.field = 'classifier'

	if f.field == 'classifier' and f.value in Registry.services.keys():  # allow queries for classifier
		f.value = f'^{f.value}:\d+$'
		f.field = 'uids'
		f.regex = True
		f.value_in_list = True

def postprocess_string( f: Filter ) -> None:
	f.value = f.value.lower() if f.value else f.value
	f.values = list( map( lambda s: s.lower(), f.values ) ) if f.values else f.values

def postprocess_date( f: Filter ) -> None:
	if f.field == 'date': # adjust field name
		f.field = 'time'

# helper functions

def unpack_filter( field, colon, expr ):
	return field, True if colon == '::' else False, expr

def unpack_filter_negate( negate, field, colon, expr ):
	return True if negate == '^' else False, field, True if colon == '::' else False, expr

def unpack_list( *args ):
	return list( map( lambda s: s.replace( ',', '' ), args ) )

def unpack_range( range_from, range_to ):
	return range_from, range_to

def unpack_date( year, month, day ):
	return year, month, day

def unpack_date_range( year_from, month_from, day_from, year_to, month_to, day_to ):
	return year_from, month_from, day_from, year_to, month_to, day_to

def unpack_time( hour, minute, second ):
	return hour, minute, second

def unpack_time_range( hour_from, minute_from, second_from, hour_to, minute_to, second_to ):
	return hour_from, minute_from, second_from, hour_to, minute_to, second_to

def _floor( year: int = None, month: int = None, day: int = None ) -> Optional[datetime]:
	if day:
		return Arrow( year, month, day ).floor( 'day' ).datetime
	elif month:
		return Arrow( year, month, 15 ).floor( 'month' ).datetime
	elif year:
		return Arrow( year, 7, 15 ).floor( 'year' ).datetime
	else:
		return Arrow( 1900, 7, 15 ).floor( 'year' ).datetime

def _ceil( year = None, month = None, day = None ) -> Optional[datetime]:
	if day:
		return Arrow( year, month, day ).ceil( 'day' ).datetime
	elif month:
		return Arrow( year, month, 15 ).ceil( 'month' ).datetime
	elif year:
		return Arrow( year, 7, 15 ).ceil( 'year' ).datetime
	else:
		return Arrow( 2099, 7, 15 ).ceil( 'year' ).datetime

def _range_of_date_keyword( keyword ) -> (Optional[date], Optional[date]):
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

def _range_of_time_keyword( keyword ) -> (Optional[time], Optional[time]):
	range_from, range_to = (None, None)

	if keyword == 'morning':
		range_from, range_to = time( 6 ), time( 11 )
	elif keyword == 'noon':
		range_from, range_to = time( 11 ), time( 13 )
	elif keyword == 'afternoon':
		range_from, range_to = time( 13 ), time( 18 )
	elif keyword == 'evening':
		range_from, range_to = time( 18 ), time( 22 )
	elif keyword == 'night':
		range_from, range_to = time( 22 ), time( 6 )

	return range_from, range_to

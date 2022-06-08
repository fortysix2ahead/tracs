
from datetime import datetime
from datetime import time
from enum import Enum
from logging import getLogger
from sys import float_info
from typing import List

import arrow
from arrow import Arrow

from tinydb.queries import Query
from tinydb.queries import QueryLike

from .config import KEY_CLASSIFER
from .config import KEY_GROUPS as GROUPS
from .filters import Filter

log = getLogger( __name__ )

FIELDS_STRING = ['name', 'type']
FIELDS_DATETIME = ['time', 'localtime']
FIELDS_TIME = []
FIELDS_INTEGER = []
FIELDS_FLOAT = []

# ----

def prepare_queries( filters: [Filter] ) -> [QueryLike]:
	return [prepare( f ) for f in (filters or [])]

def prepare( filter: Filter ) -> QueryLike:
	if filter is None:
		return Filter.false()

	# filter is already callable -> return it (intermediate solution until we can clean the prepare method)
	if filter.callable:
		return filter

	log.warning( f'using deprecated filter prepare: {filter}' )

	if filter.classifier is None:
		if not filter.value and not filter.range_from and not filter.range_to:
			q = is_empty( filter.field )
		elif filter.field == 'raw_id' or filter.field == 'sid' or filter.field == 'uid':
			q = has_raw_id( filter.value )
		elif filter.field in ['service', 'source']:
			q = query_service( filter.value )
		elif filter.field == 'type':
			q = enum_is( 'type', filter.value )
		elif filter.field == 'date':
			q = datetime_in_range( 'time', filter.range_from, filter.range_to )
		elif filter.field == 'time':
			if filter.value:
				q = time_is( filter.field, filter.value )
			elif filter.range_from and filter.range_to:
				q = time_in_range( filter.field, filter.range_from, filter.range_to )
		elif isinstance( filter.value, (int, float) ):
			q = field_is( filter.field, filter.value )
		elif isinstance( filter.range_from, (int, float) ) or isinstance( filter.range_to, (int, float) ):
			q = field_in_range( filter.field, filter.range_from, filter.range_to )
#		elif filter.field in FIELDS_STRING:
#			q = query_field_match( filter.field, filter.value )
		else:
			q = Filter.false()
	else:
		q = Filter.false()

	return q if (filter.negate == False) else ~ q

# ---- collection of predefined queries -----

def query_true() -> QueryLike:
	return Filter.true()

def query_all( include_groups: bool = True, include_grouped: bool = False, include_ungrouped = True ) -> QueryLike:
	params = (include_groups, include_grouped, include_ungrouped)
	q_groups = is_group()
	q_grouped = is_grouped()
	q_ungrouped = is_ungrouped()

	if params == (True, True, True):
		return query_true()
	elif params == (True, True, False):
		return q_groups | q_grouped
	elif params == (True, False, True):
		return q_groups | q_ungrouped
	elif params == (True, False, False):
		return q_groups
	elif params == (False, True, True):
		return q_grouped | q_ungrouped
	elif params == (False, True, False):
		return q_grouped
	elif params == (False, False, True):
		return q_ungrouped
	elif params == (False, False, False):
		return Filter.false()

def field_exists( field: str ) -> Query:
	return Query()[field].exists()

def field_is( field: str, value ) -> Query:
	"""
	Matches if value == activity[field].

	:param field: field name
	:param value: value
	:return: match result
	"""
	return Query()[field] == value

def field_in_range( field: str, _from: float = None, _to: float = None ) -> Query:
	_from = _from if _from else float_info.min
	_to = _to if _to else float_info.max
	return is_number( field ) & (Query()[field] >= _from) & (Query()[field] < _to)

def field_in_list( field: str, sequence: List ) -> Query:
	"""
	Matches if activity[field] is contained in sequence.

	:param field: field name
	:param sequence: sequence of values
	:return: match result
	"""
	return Query()[field].one_of( sequence )

def has_id( id: int ) -> Query:
	return field_is( 'id', id )

def has_raw_id( raw_id: int ) -> Query:
	return field_is( 'raw_id', raw_id )

def query_service( service_name: str ) -> Query:
	def fn( value, service: str ) -> bool:
		return any( v.startswith( service ) for v in value )

	q_service = field_is( KEY_CLASSIFER, service_name )
	q_service_grouped = Query()[GROUPS]['uids'].test( fn, service_name )
	return q_service | q_service_grouped

def query_service_id( service_name: str, id: int ) -> Query:
	if service_name:
		return has_raw_id( id ) & query_service( service_name )
	else:
		return has_raw_id( id )

def is_empty( field: str ) -> Query:
	return Query()[field].test( lambda v: v is None or v == '' )

def is_number( field: str ) -> Query:
	return Query()[field].test( lambda v: isinstance( v, (float,int) ) )

def is_string( field: str ) -> Query:
	return Query()[field].test( lambda v: isinstance( v, str ) )

def is_group() -> Query:
	return (Query()[GROUPS]['ids'].exists()) | (Query()[GROUPS]['uids'].exists())

def is_grouped() -> Query:
	return Query()[GROUPS]['parent'].exists()

def list_not_empty( map_field: str, field: str ) -> Query:
	"""
	Query for lists in x[map_field][field] have a length greater 0.

	:param map_field: map field name
	:param field: field name
	:return: result of the query evaluation
	"""
	def fn( value ) -> bool:
		return True if len( value ) > 0 else False
	return Query()[map_field][field].test( fn )

def query_grouped_by( service_name: str ) -> Query:
	if service_name:
		return Query()[GROUPS]['parent'].exists() & Query()[KEY_CLASSIFER] == service_name
	else:
		return Query()[GROUPS]['parent'].exists()

def is_ungrouped() -> Query:
	def fn( value ) -> bool:
		return True if not value or len( value ) == 0 else False
	return (~ Query()[GROUPS].exists()) | ( Query()[GROUPS].test( fn ) )

def has_time() -> Query:
	return field_exists( 'time' )

def datetime_in_range( field: str, from_time: Arrow or datetime, to_time: Arrow or datetime ) -> Query:
	def fn( value, _from: Arrow, _to: Arrow ) -> bool:
		if _from <= value <= _to:
			return True
		return False

	from_time = arrow.get( from_time ) if type( from_time ) is datetime else from_time
	to_time = arrow.get( to_time ) if type( to_time ) is datetime else to_time

	return Query()[field].map( lambda t: arrow.get( t ) ).test( fn, from_time, to_time )

def time_is( field: str, tm: time or datetime or Arrow ) -> Query:
	def fn( value: time, _tm: time ) -> bool:
		if value == _tm:
			return True
		else:
			return False

	tm = tm.time() if type( tm ) in [datetime, Arrow] else tm

	return Query()[field].map( lambda t: arrow.get( t ).time() ).test( fn, tm )

def time_in_range( field: str, from_time: time or datetime or Arrow, to_time: time or datetime or Arrow ) -> Query:
	def fn( value: time, _from_time: time, _to_time: time ) -> bool:
		if _from_time <= value < _to_time:
			return True
		else:
			return False

	from_time = from_time.time() if type( from_time ) in [datetime, Arrow] else from_time
	to_time = to_time.time() if type( to_time ) in [datetime, Arrow] else to_time

	return Query()[field].map( lambda t: arrow.get( t ).time() ).test( fn, from_time, to_time )

def enum_is( enum_field: str, enum_value: str ) -> Query:
	def fn( e, value ):
		if isinstance( e, Enum ) and e.name == value:
			return True
		else:
			return False

	return Query()[enum_field].test( fn, enum_value )
#	return Query()[enum_field].name == value

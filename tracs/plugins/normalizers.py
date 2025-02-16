from datetime import datetime
from re import fullmatch

from dateutil.tz import UTC

from tracs.core import Normalizer
from tracs.pluginmgr import normalizer
from tracs.rules import DATE_RANGE_PATTERN, FUZZY_DATE_PATTERN, FUZZY_TIME_PATTERN, parse_date_range_as_str, parse_time_range, TIME_RANGE_PATTERN
from tracs.utils import floor_ceil_from

YEAR_RANGE = range( 2000, datetime.now( UTC ).year + 1 )

@normalizer
def classifier() -> Normalizer:
	return Normalizer(
		'classifier',
		str,
		'tests if a provided classifier is contained in the list of classifiers of an activity',
		lambda l, o, r, nr: f'"{r}" in classifiers'
	)

@normalizer
def service() -> Normalizer:
	return Normalizer(
		'service',
		str,
		'alias for classifier',
		lambda l, o, r, nr: f'"{r}" in classifiers'
	)

@normalizer
def source() -> Normalizer:
	return Normalizer(
		'source',
		str,
		'alias for classifier',
		lambda l, o, r, nr: f'"{r}" in classifiers'
	)

@normalizer
def type() -> Normalizer:
	return Normalizer(
		'type',
		str,
		'normalizer to support filtering for type names',
		lambda l, o, r, nr: f'type.name == "{r.lower()}"'
	)

@normalizer
def id() -> Normalizer:
	def fn( left, op, right, rule ) -> str:
		try:
			return f'year == {right}' if int( right ) in YEAR_RANGE else rule
		except (TypeError, ValueError):
			return rule

	return Normalizer( 'id', int, 'treat ids from 2000 to current year as years rather than ids', fn )

@normalizer
def date() -> Normalizer:
	def fn( left, op, right, rule ) -> str:
		if fullmatch( FUZZY_DATE_PATTERN, right ):
			return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
		elif DATE_RANGE_PATTERN.fullmatch( right ):
			return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *parse_date_range_as_str( right ) )
		else:
			return rule

	return Normalizer( 'date', datetime, 'allow access to date via provided date string', fn )

@normalizer
def time() -> Normalizer:
	def fn( left, op, right, rule ) -> str:
		if fullmatch( FUZZY_TIME_PATTERN, right ):
			return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
		elif TIME_RANGE_PATTERN.fullmatch( right ):
			return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *parse_time_range( right, as_str=True ) )
		else:
			return rule

	return Normalizer( 'time', datetime, 'allow access to localtime via provided time string', fn )

from datetime import datetime, timedelta

from arrow import Arrow, get
from dateutil.tz import UTC

from rules import DATE_RANGE, TIME_RANGE
from tracs.core import Normalizer
from tracs.pluginmgr import normalizer
from tracs.rules import FUZZY_DATE, FUZZY_TIME
from tracs.utils import timedelta_to_iso8601

YEAR_RANGE = range( 2000, datetime.now( UTC ).year + 1 )

@normalizer
def classifier() -> Normalizer:
	return Normalizer(
		'classifier',
		str,
		'tests if a provided classifier is contained in the list of classifiers of an activity',
		lambda l, o, r, nr = None: f'"{r}" in classifiers'
	)

@normalizer
def service() -> Normalizer:
	return Normalizer(
		'service',
		str,
		'alias for classifier',
		lambda l, o, r, nr = None: f'"{r}" in classifiers'
	)

@normalizer
def source() -> Normalizer:
	return Normalizer(
		'source',
		str,
		'alias for classifier',
		lambda l, o, r, nr = None: f'"{r}" in classifiers'
	)

@normalizer
def type() -> Normalizer:
	return Normalizer(
		'type',
		str,
		'normalizer to support filtering for type names',
		lambda l, o, r, nr = None: f'type&.name == "{r}".as_lower'
	)

# deactivate normalizer as treating int differently is confusing -> more to optional plugin?
# @normalizer
# def id() -> Normalizer:
# 	def fn( left, op, right, rule ) -> str:
# 		try:
# 			return f'year == {right}' if int( right ) in YEAR_RANGE else rule
# 		except (TypeError, ValueError):
# 			return rule
#
# 	return Normalizer( 'id', int, 'treat ids from 2000 to current year as years rather than ids', fn )

@normalizer
def date() -> Normalizer:
	def fn( left, op, right, rule = None ) -> str:

		if m := FUZZY_DATE.fullmatch( right ):
			year, month, day = m.groups()

			rule = f'starttime_local&.year == {int( year )}'
			rule = f'{rule} and starttime_local&.month == {int( month )}' if month else rule
			rule = f'{rule} and starttime_local&.day == {int( day )}' if day else rule

		elif m := DATE_RANGE.fullmatch( right ):
			year_from, month_from, day_from, year_to, month_to, day_to = m.groups()

			if day_from:
				date_from = get( int( year_from ), int( month_from ), int( day_from ) ).floor( 'day' )
			elif month_from:
				date_from = get( int( year_from ), int( month_from ), 1 ).floor( 'month' )
			elif year_from:
				date_from = get( int( year_from ), 1, 1 ).floor( 'year' )
			else:
				date_from = get( 1970 ).floor( 'year' )

			if day_to:
				date_to = get( int( year_to ), int( month_to ), int( day_to ) ).ceil( 'day' )
			elif month_to:
				date_to = get( int( year_to ), int( month_to ), 31 ).ceil( 'month' )
			elif year_to:
				date_to = get( int( year_to ), 12, 31 ).ceil( 'year' )
			else:
				date_to = get( 2099, 12, 31 ).ceil( 'year' )

			rule = f'starttime_local >= d"{date_from.isoformat()}" and starttime_local <= d"{date_to.isoformat()}"'

		return rule

	return Normalizer( 'date', datetime, 'allow access to date via provided date string', fn )

# @normalizer
# def date() -> Normalizer:
# 	def fn( left, op, right, rule ) -> str:
# 		if fullmatch( FUZZY_DATE_PATTERN, right ):
# 			return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
# 		elif DATE_RANGE.fullmatch( right ):
# 			return 'starttime_local >= d"{}" and starttime_local <= d"{}"'.format( *parse_date_range_as_str( right ) )
# 		else:
# 			return rule
#
# 	return Normalizer( 'date', datetime, 'allow access to date via provided date string', fn )

@normalizer
def time() -> Normalizer:

	def fn( left, op, right, rule = None ) -> str:
		if m := FUZZY_TIME.fullmatch( right ):
			hour, minute, second = m.groups()

			rule = f'starttime_local&.hour == {int( hour )}'
			rule = f'{rule} and starttime_local&.minute == {int( minute )}' if minute else rule
			rule = f'{rule} and starttime_local&.second == {int( second )}' if second else rule

		elif m := TIME_RANGE.fullmatch( right ):
			hour_from, minute_from, second_from, hour_to, minute_to, second_to = m.groups()

			if second_from:
				time_from = Arrow(2000, 1, 1, hour=int( hour_from ), minute=int( minute_from ), second=int( second_from ) )
			elif minute_from:
				time_from = Arrow(2000, 1, 1, hour=int( hour_from ), minute=int( minute_from ), second=0 )
			elif hour_from:
				time_from = Arrow(2000, 1, 1, hour=int( hour_from ), minute=0, second=0 )
			else:
				time_from = Arrow(2000, 1, 1, hour=0, minute=0, second=0 )

			if second_to:
				time_to = Arrow( 2000, 1, 1, hour=int( hour_to ), minute=int( minute_to ), second=int( second_to ) ).ceil( 'second' )
			elif minute_to:
				time_to = Arrow( 2000, 1, 1, hour=int( hour_to ), minute=int( minute_to ), second=0 )
			elif hour_to:
				time_to = Arrow( 2000, 1, 1, hour=int( hour_to ), minute=0, second=0 )
			else:
				time_to = Arrow( 2000, 1, 1, hour=23, minute=59, second=59 ).ceil( 'second' )

			time_from = timedelta( hours=time_from.hour, minutes=time_from.minute, seconds=time_from.second )
			time_to = timedelta( hours=time_to.hour, minutes=time_to.minute, seconds=time_to.second )

			rule = f'time >= t"{timedelta_to_iso8601( time_from )}" and time <= t"{timedelta_to_iso8601( time_to )}"'

		return rule

	return Normalizer( 'time', datetime, 'allow access to localtime via provided time string', fn )

# @normalizer
# def time() -> Normalizer:
# 	def fn( left, op, right, rule ) -> str:
# 		if fullmatch( FUZZY_TIME, right ):
# 			return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *floor_ceil_from( right, as_str=True ) )
# 		elif TIME_RANGE_PATTERN.fullmatch( right ):
# 			return '__time__ >= d"{}" and __time__ <= d"{}"'.format( *parse_time_range( right, as_str=True ) )
# 		else:
# 			return rule
#
# 	return Normalizer( 'time', datetime, 'allow access to localtime via provided time string', fn )


from datetime import date as pydate, datetime, time as pytime, timedelta

from tracs.pluginmgr import derived_field

# derived fields to extend Activity class

#@derived_field(
#	display_name='Classifiers',
#	description='list of classifiers of an activity',
#	type=List[str],
#)
#def classifiers( self ) -> List[str]:
#	return list( map( lambda s: s.split( ':', 1 )[0], self.iter_uid_heads ) )

@derived_field(
	display_name='Year',
	description='year in which the activity has taken place',
	type=int,
)
def year( self ) -> int:
	return self.starttime_local.year

@derived_field(
	display_name='Month',
	description='month in which the activity has taken place',
	type=int,
)
def month( self ) -> int:
	return self.starttime_local.month

@derived_field(
	display_name='Day',
	description='day on which the activity has taken place',
	type=int,
)
def day( self ) -> int:
	return self.starttime_local.day

@derived_field(
	display_name='Weekday',
	description='day of week at which the activity has taken place (as number)',
	type=int,
)
def weekday( self ) -> int:
	return self.starttime_local.weekday()

@derived_field(
	display_name='Hour',
	description='hour in which the activity has been started',
	type=int,
)
def hour( self ) -> int:
	return self.starttime_local.hour


@derived_field(
	display_name='Date',
	description='Date without time',
	type=timedelta,
	expose=False,
)
def date( self ) -> timedelta:
	return timedelta( days=self.starttime_local.timetuple().tm_yday )

@derived_field(
	display_name='Time',
	description='Local time without date',
	type=timedelta,
	expose=False,
)
def time( self ) -> timedelta:
	return timedelta( hours=self.starttime_local.hour, minutes=self.starttime_local.minute, seconds=self.starttime_local.second )

@derived_field(
	display_name='Local Date',
	description='Local date without time',
	type=pydate,
	expose=False,
)
def _date( self ) -> pydate:
	# rules does not care about timezones -> that's why we need to return time without tz information
	return pydate( self.starttime_local.year, self.starttime_local.month, self.starttime_local.day )

@derived_field(
	display_name='Local Time',
	description='Local time without date and tz',
	type=datetime,
	expose=False,
)
def _time( self ) -> datetime:
	# rules does not care about timezones -> that's why we need to return time without tz information
	return datetime( 1, 1, 1, self.starttime_local.hour, self.starttime_local.minute, self.starttime_local.second )
	# return pytime( self.starttime_local.hour, self.starttime_local.minute, self.starttime_local.second )

from datetime import datetime, timedelta
from typing import List

from tracs.core import VirtualField
from tracs.pluginmgr import virtualfield

# virtual fields

@virtualfield
def classifiers() -> VirtualField:
	return VirtualField( 'classifiers', List[str], display_name='Classifiers', description='list of classifiers of an activity',
	                     factory=lambda a: list( map( lambda s: s.split( ':', 1 )[0], a.uids ) ) )

@virtualfield
def weekday() -> VirtualField:
	return VirtualField( 'weekday', int, display_name='Weekday', description='day of week at which the activity has taken place (as number)',
	                     factory=lambda a: a.starttime_local.year )

@virtualfield
def hour() -> VirtualField:
	return VirtualField( 'hour', int, display_name='Hour of Day', description='hour in which the activity has been started',
	                     factory=lambda a: a.starttime_local.hour )

@virtualfield
def day() -> VirtualField:
	return VirtualField( 'day', int, display_name='Day of Month', description='day on which the activity has taken place',
	                     factory=lambda a: a.starttime_local.day )

@virtualfield
def month() -> VirtualField:
	return VirtualField( 'month', int, display_name='Month', description='month in which the activity has taken place',
	                     factory=lambda a: a.starttime_local.month )

@virtualfield
def year() -> VirtualField:
	return VirtualField( 'year', int, display_name='Year', description='year in which the activity has taken place', factory=lambda a: a.starttime_local.year )

@virtualfield
def date() -> VirtualField:
	return VirtualField( 'date', timedelta, display_name='Date', description='Date without date',
	                     factory=lambda a: timedelta( days=a.starttime_local.timetuple().tm_yday ) )

@virtualfield
def time() -> VirtualField:
	return VirtualField( 'time', timedelta, display_name='Time', description='Local time without date',
	                     factory=lambda a: timedelta( hours=a.starttime_local.hour, minutes=a.starttime_local.minute, seconds=a.starttime_local.second ) )

@virtualfield
def time_dt() -> VirtualField:
	return VirtualField( '__time__', datetime, display_name='Time (datetime)', description='local time without a date and tz',
	                     # rules does not care about timezones -> that's why we need to return time without tz information
	                     # lambda a: datetime( 1, 1, 1, a.localtime.hour, a.localtime.minute, a.localtime.second, tzinfo=UTC ),
	                     factory=lambda a: datetime( 1, 1, 1, a.starttime_local.hour, a.starttime_local.minute, a.starttime_local.second ) )


from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone

from dateutil.tz import gettz
from dateutil.tz import tzlocal

from tracs.activity_types import ActivityTypes
from tracs.utils import as_datetime
from tracs.utils import fmt
from tracs.utils import seconds_to_time
from tracs.utils import fromisoformat
from tracs.utils import fromtimezone
from tracs.utils import toisoformat

def test_fmt():
	assert fmt( None ) == ''
	assert fmt( '' ) == ''

	assert fmt( 0 ) == '0'
	assert fmt( 100 ) == '100'
	assert fmt( -10 ) == '-10'

	assert fmt( 100.12345 ) == '100.1'
	assert fmt( -100.12345 ) == '-100.1'

	assert fmt( '100' ) == '100'
	assert fmt( '100.12345' ) == '100.1'

	assert fmt( 'abcd' ) == 'abcd'

	assert fmt( '2020-02-01T10:20:30+00:00' ) == "Feb 1, 2020, 10:20:30 AM"
	assert fmt( datetime( 2020, 2, 1, 10, 20, 30 ) ) == "Feb 1, 2020, 10:20:30 AM"

	assert fmt( date( 2019, 4, 25 ) ) == 'Apr 25, 2019'
	assert fmt( time( 10, 19, 25 ) ) == '10:19:25 AM'
	assert fmt( time( 14, 19, 25 ) ) == '2:19:25 PM'

	td = datetime( 2020, 2, 1, 10, 20, 30 ) - datetime( 2020, 2, 1, 10, 20, 33 )
	assert fmt( td ) == '3 sec'
	td = datetime( 2020, 2, 1, 10, 20, 30 ) - datetime( 2020, 2, 1, 10, 21, 33 )
	assert fmt( td ) == '63 sec'
	td = datetime( 2020, 2, 1, 10, 20, 30 ) - datetime( 2020, 2, 1, 10, 23, 33 )
	assert fmt( td ) == '3 min'
	td = datetime( 2020, 2, 1, 10, 20, 30 ) - datetime( 2020, 2, 1, 10, 30, 41 )
	assert fmt( td ) == '10 min'
	td = datetime( 2020, 2, 1, 11, 47, 30 ) - datetime( 2020, 2, 1, 10, 30, 41 )
	assert fmt( td ) == '77 min'

	assert fmt( ActivityTypes.drive ) == 'Driving'

def test_localized_fmt():
	assert fmt( 100.12345, 'de' ) == '100,1'
	assert fmt( -100.12345, 'de' ) == '-100,1'

	assert fmt( '2020-02-01T10:20:30+00:00', 'de' ) == "01.02.2020, 10:20:30"
	assert fmt( datetime( 2020, 2, 1, 10, 20, 30 ), 'de' ) == "01.02.2020, 10:20:30"

	assert fmt( date( 2019, 4, 25 ), 'de' ) == '25.04.2019'
	assert fmt( time( 10, 19, 25 ), 'de' ) == '10:19:25'
	assert fmt( time( 14, 19, 25 ), 'de' ) == '14:19:25'

def test_seconds_to_time():
	assert seconds_to_time( None ) is None
	assert seconds_to_time( '' ) is None

	assert seconds_to_time( 62 ) == time( 0, 1, 2 )
	assert seconds_to_time( 100.3 ) == time( 0, 1, 40 )
	assert seconds_to_time( 121.7 ) == time( 0, 2, 2 )

def test_fromisoformat():
	assert fromisoformat( '2020-02-01T10:20:30+00:00' ) == datetime( 2020, 2, 1, 10, 20, 30, tzinfo=timezone.utc )
	assert fromisoformat( '2020-02-01T10:20:30Z' ) == datetime( 2020, 2, 1, 10, 20, 30, tzinfo=timezone.utc )
	assert fromisoformat( datetime( 2020, 2, 1, 10, 20, 30 ) ) == datetime( 2020, 2, 1, 10, 20, 30 )
	assert fromisoformat( '10:20:30' ) == time( 10, 20, 30 )
	assert fromisoformat( time( 10, 20, 30 ) ) == time( 10, 20, 30 )
	assert fromisoformat( 'invalid' ) is None
	assert fromisoformat( None ) is None

def test_toisoformat():
	assert toisoformat( datetime( 2020, 2, 1, 10, 20, 30, tzinfo=timezone.utc ) ) == '2020-02-01T10:20:30+00:00'
	assert toisoformat( time( 10, 20, 30 ) ) == '10:20:30'
	assert toisoformat( '2020-02-01T10:20:30+00:00' ) == '2020-02-01T10:20:30+00:00'
	assert toisoformat( 'invalid' ) == 'invalid'

def test_as_time():
	ts = 946684800 # new year 2000 UTC
	assert as_datetime( ts=ts ) == datetime( 2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc )
	assert as_datetime( ts=ts, tz=gettz() ) == datetime( 2000, 1, 1, 1, 0, 0, tzinfo=gettz() )
	assert as_datetime( ts=ts, tzstr='Europe/Berlin' ) == datetime( 2000, 1, 1, 1, 0, 0, tzinfo=gettz( 'Europe/Berlin' ) )
	assert as_datetime( ts=ts, tz=timezone.utc, tzstr='Europe/Berlin' ) == datetime( 2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc )

	ts = 946684800000 # new year 2000 UTC, millisecond precision
	assert as_datetime( ts=ts ) == datetime( 2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc )

	dt = datetime( 2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc )
	assert as_datetime( dt ) == dt
	assert as_datetime( dt, tz=gettz() ) == datetime( 2000, 1, 1, 1, 0, 0, tzinfo=gettz() )
	assert as_datetime( dt, tz=timezone.utc, tzstr='Europe/Berlin' ) == datetime( 2000, 1, 1, 1, 0, 0, tzinfo=gettz() )

	dt_iso = '2000-01-01T00:00:00+00:00'
	assert as_datetime( dtstr=dt_iso ) == dt
	assert as_datetime( dtstr=dt_iso, tz=gettz() ) == datetime( 2000, 1, 1, 1, 0, 0, tzinfo=gettz() )
	dt_iso = '2000-01-01T01:00:00+01:00'
	assert as_datetime( dtstr=dt_iso ) == datetime( 2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc )

	assert as_datetime( None ) is None
	assert as_datetime( '' ) is None

def test_fromtimezone():
	tz1 = gettz()
	print( tz1 )
	tz2 = gettz( 'Europe/Berlin' )
	print( tz2 )
	tz3 = tzlocal()
	print( tz3 )
	assert fromtimezone( None ) == tzlocal()
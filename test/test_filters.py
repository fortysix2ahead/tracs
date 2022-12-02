
from re import match
from sys import float_info
from typing import List

from arrow import Arrow as dt
from arrow import now
from datetime import datetime
from datetime import time

from dateutil.tz import UTC
from pytest import mark
from sys import maxsize
from tinydb.queries import QueryLike

from tracs.activity_types import ActivityTypes
from tracs.filters import false
from tracs.filters import invalid
from tracs.filters import parse
from tracs.filters import resource_pattern
from tracs.filters import true
from tracs.filters import Filter
from tracs.filters import filter_pattern2
from tracs.filters import TYPES
from tracs.plugins.polar import Polar
from tracs.registry import Registry

from .helpers import ids

def test_predefined_filters():
	assert false().callable is not None
	assert false().valid == True

	assert true().callable is not None
	assert true().valid == True

	assert invalid().callable is not None
	assert invalid().valid == False

def test_filter_pattern():
	assert not match( filter_pattern2, '^' )
	assert not match( filter_pattern2, '1000' )
	assert not match( filter_pattern2, '^1000' )

	assert not match( filter_pattern2, '1000,1001,1002' )
	assert not match( filter_pattern2, '^1000,1001,1002' )

	assert match( filter_pattern2, 'id:1000' )
	assert match( filter_pattern2, '^id:1000' )
	assert match( filter_pattern2, 'ID:1000' )

	assert match( filter_pattern2, 'local_id:1000' )
	assert match( filter_pattern2, '^local_id:1000' )

	assert match( filter_pattern2, 'id:1000,1001,1002' )
	assert match( filter_pattern2, 'id:1000..1002' )

	assert match( filter_pattern2, 'date:2020-01-15..2021-09-01' )

	assert match( filter_pattern2, 'location:berlin' )

	assert match( resource_pattern, 'polar:1000#1' )
	assert match( resource_pattern, 'polar:1000#gpx' )
	# assert match( resource_pattern, 'polar:1000?1001.gpx' )
	assert match( resource_pattern, 'polar:1001#application/xml+gpx' )
	assert match( resource_pattern, 'polar:1001#application/xml+gpx-polar' )

def test_parse():
	# special cases first
	assert not parse( '^' ).valid # invalid only is invalid ...

	# integer number is interpreted as id
	assert parse( '1000' ) == Filter( 'id', 1000 ) # number is assumed to be an id
	assert parse( '^1000' ) == Filter( 'id', 1000, negate=True ) # negate also works on id (does not make much sense however ...)

	# list of ids
	assert parse( '1000,1001,1002' ) == Filter( 'id', [1000, 1001, 1002] )
	assert parse( '^1000,1001,1002' ) == Filter( 'id', [1000, 1001, 1002], negate=True )

	# range of ids
	assert parse( '1000..1002' ) == Filter( 'id', (1000, 1002) )
	assert parse( '1000..' ) == Filter( 'id', (1000, maxsize ) )
	assert parse( '..1002' ) == Filter( 'id', (~maxsize, 1002 ) )
	assert parse( '^1000..1002' ) == Filter( 'id', (1000, 1002), negate=True )
	assert not parse( '..' ).valid # empty range is invalid

	assert parse( 'id:1000' ) == Filter( 'id', 1000 )
	assert parse( '^id:1000' ) == Filter( 'id', 1000, negate=True )
	assert parse( 'id:' ) == Filter( 'id' )
	assert parse( 'id:1000..' ) == Filter( 'id', (1000, maxsize) )
	assert parse( 'id:..1010' ) == Filter( 'id', (~maxsize, 1010 ) )
	assert parse( 'id:1000..1010' ) == Filter( 'id', (1000, 1010 ) )
	assert parse( 'id:1000,1001,1002' ) == Filter( 'id', [1000, 1001, 1002] )

	# non-existing field
	assert not parse( 'invalid_filter:1000' ).valid

	# strings as values
	assert parse( 'name:Run1' ) == Filter( 'name', 'run1' )
	assert parse( 'name:"Run 5K in 2021"' ) == Filter( 'name', 'run 5k in 2021' )
	assert parse( 'name:run,hike,walk' ) == Filter( 'name', ['run', 'hike', 'walk'] )
	assert parse( 'name:' ) == Filter( 'name', None )

	# aliases
	assert parse( 'location_place:forest' ) == Filter( 'location_place', 'forest' )
	assert parse( 'place:forest' ) == Filter( 'location_place', 'forest' )

	# numbers as values
	assert parse( 'distance:5000' ) == Filter( 'distance', int( 5000 ) )
	assert parse( 'distance:5500.55' ) == Filter( 'distance', 5500.55 )
	assert parse( 'distance:5000..6000' ) == Filter( 'distance', (5000, 6000) )
	assert parse( 'distance:5000..' ) == Filter( 'distance', (5000, float_info.max) )
	assert parse( 'distance:..6000' ) == Filter( 'distance', (float_info.min, 6000) )
	assert parse( 'distance:5000.0..6000.0' ) == Filter( 'distance', (5000.0, 6000.0) )
	assert parse( 'distance:5000.0..' ) == Filter( 'distance', (5000.0, float_info.max) )
	assert parse( 'distance:..6000.0' ) == Filter( 'distance', (float_info.min, 6000.0) )
	assert parse( 'distance:' ) == Filter( 'distance' )

	assert parse( 'date:2020' ) == Filter( 'time', (_fyear( 2020 ), _cyear( 2020 )) )
	assert parse( 'date:..2020' ) == Filter( 'time', (_fyear( 1900 ), _cyear( 2020 )) )
	assert parse( 'date:2020..' ) == Filter( 'time', (_fyear( 2020 ), _cyear( 2099 )) )
	assert parse( 'date:2020..2021' ) == Filter( 'time', (_fyear( 2020 ), _cyear( 2021 )) )

	assert parse( 'date:2020-05' ) == Filter( 'time', (_fmonth( 2020, 5 ), _cmonth( 2020, 5 )) )
	assert parse( 'date:2020-05..' ) == Filter( 'time', (_fmonth( 2020, 5 ), _cyear( 2099 )) )
	assert parse( 'date:..2020-05' ) == Filter( 'time', (_fyear( 1900 ), _cmonth( 2020, 5 )) )
	assert parse( 'date:2020-02..2020-05' ) == Filter( 'time', (_fmonth( 2020, 2 ), _cmonth( 2020, 5 )) )

	assert parse( 'date:2020-05-17' ) == Filter( 'time', (_fday( 2020, 5, 17 ), _cday( 2020, 5, 17 )) )
	assert parse( 'date:2020-05-17..' ) == Filter( 'time', (_fday( 2020, 5, 17 ), _cyear( 2099 )) )
	assert parse( 'date:..2020-05-17' ) == Filter( 'time', (_fyear( 1900 ), _cday( 2020, 5, 17 )) )
	assert parse( 'date:2020-05-04..2020-05-17' ) == Filter( 'time', (_fday( 2020, 5, 4 ), _cday( 2020, 5, 17 )) )

#	assert parse( 'date:latest' ) == Filter( 'date', value='latest' )
#	assert parse( 'date:lastweek' ) == (None, 'time', 'lastweek', None, None, False)

	n = now()
	assert parse( 'date:today' ) == Filter( 'time', (n.floor( 'day' ), n.ceil( 'day' )) )
	assert parse( 'date:thisweek' ) == Filter( 'time', (n.floor( 'week' ), n.ceil( 'week' )) )
	assert parse( 'date:thismonth' ) == Filter( 'time', (n.floor( 'month' ), n.ceil( 'month' )) )
	assert parse( 'date:thisquarter' ) == Filter( 'time', (n.floor( 'quarter' ), n.ceil( 'quarter' )) )
	assert parse( 'date:thisyear' ) == Filter( 'time', (n.floor( 'year' ), n.ceil( 'year' )) )

	ns = now().shift( days=-6 )
	assert parse( 'date:last7days' ) == Filter( 'time', (ns.floor( 'day' ), n.ceil( 'day' )) )

	ns = now().shift( days=-29 )
	assert parse( 'date:last30days' ) == Filter( 'time', (ns.floor( 'day' ), n.ceil( 'day' )) )

	ns = now().shift( days=-59 )
	assert parse( 'date:last60days' ) == Filter( 'time', (ns.floor( 'day' ), n.ceil( 'day' )) )

	ns = now().shift( days=-89 )
	assert parse( 'date:last90days' ) == Filter( 'time', (ns.floor( 'day' ), n.ceil( 'day' )) )

	ns = now().shift( days=-1 )
	assert parse( 'date:yesterday' ) == Filter( 'time', (ns.floor( 'day' ), ns.ceil( 'day' )) )
	ns = now().shift( weeks=-1 )
	assert parse( 'date:lastweek' ) == Filter( 'time', (ns.floor( 'week' ), ns.ceil( 'week' )) )
	ns = now().shift( months=-1 )
	assert parse( 'date:lastmonth' ) == Filter( 'time', (ns.floor( 'month' ), ns.ceil( 'month' )) )
	ns = now().shift( months=-3 )
	assert parse( 'date:lastquarter' ) == Filter( 'time', (ns.floor( 'quarter' ), ns.ceil( 'quarter' )) )
	ns = now().shift( years=-1 )
	assert parse( 'date:lastyear' ) == Filter( 'time', (ns.floor( 'year' ), ns.ceil( 'year' )) )

	# exact times
	assert parse( 'time:15' ) == Filter( 'time', time( 15 ) )
	assert parse( 'time:15:00' ) == Filter( 'time', time( 15, 0 ) )
	assert parse( 'time:15:00:07' ) == Filter( 'time', time( 15, 0, 7 ) )
	# leaving out the colons also works
	assert parse( 'time:1500' ) == Filter( 'time', time( 15, 0 ) )
	assert parse( 'time:150007' ) == Filter( 'time', time( 15, 0, 7 ) )

	# time ranges
	assert parse( 'time:15..17' ) == Filter( 'time', (time( 15 ), time( 17 ) ) )
	assert parse( 'time:..17' ) == Filter( 'time', ( time( 0 ), time( 17 ) ) )
	assert parse( 'time:15..' ) == Filter( 'time', (time( 15 ), time( 0 ) ) )
	assert parse( 'time:15:00..17:00' ) == Filter( 'time', (time( 15 ), time( 17 ) ) )
	assert parse( 'time:15:00:05..17:00:07' ) == Filter( 'time', (time( 15, 0, 5 ), time( 17, 0, 7 ) ) )
	assert parse( 'time:150005..1700' ) == Filter( 'time', (time( 15, 0, 5 ), time( 17, 0, 0 ) ) )

	# time keywords
	assert parse( 'time:morning' ) == Filter( 'time', (time( 6 ), ( time( 11 ) ) ) ) # 06 to 11
	assert parse( 'time:noon' ) == Filter( 'time', (time( 11 ), ( time( 13 ) ) ) ) # 11 to 13
	assert parse( 'time:afternoon' ) == Filter( 'time', (time( 13 ), ( time( 18 ) ) ) ) # 13 to 18
	assert parse( 'time:evening' ) == Filter( 'time', (time( 18 ), ( time( 22 ) ) ) ) # 18 to 22
	assert parse( 'time:night' ) == Filter( 'time', (time( 22 ), ( time( 6 ) ) ))  # 22 to 06

	# types
	assert parse( 'type:run' ) == Filter( 'type', 'run' )

	# special cases

	# special treament for uids
	# polar as service name is not registered yet -> do it for this test case
	Registry.services['polar'] = Polar( base_url='http://example.com' )
	TYPES['polar'] = 'int'
	assert parse( 'polar:123456' ) == Filter( 'uids', 'polar:123456', regex=False )
	# treatment of classifiers
	assert parse( 'classifier:polar' ) == Filter( 'uids', value='^polar:\\d+$', regex=True, value_in_list=True )

@mark.db( template='default', inmemory=True )
def test_filters_on_activities( db ):
	m = {} # map with all doc_id -> activities
	for a in db.activities.all():
		m[a.doc_id] = a

	def length( q: QueryLike ) -> int:
		return len( list( filter( q, m.values() ) ) )

	# true
	assert true()( m[1] )
	assert length( true() ) == len( m.items() )

	# false
	assert not false()( m[1] )
	assert length( false() ) == 0

	# has_id, equal to value
	assert Filter( field='id', value=1 )( m[1] )
	assert not Filter( field='id', value=1, negate=True )( m[1] )
	assert not Filter( field='id', value=1 )( m[2] )
	assert Filter( field='id', value=1, negate=True )( m[2] )

	# list of ids
	assert Filter( field='id', value=[1, 3, 5] )( m[1] )
	assert not Filter( field='id', value=[0, 2, 4] )( m[1] )

	# range of ids
	assert Filter( field='id', value=(1, 2) )( m[1] )
	assert Filter( field='id', value=(1, 2) )( m[2] )
	assert not Filter( field='id', value=(1, 2) )( m[3] )

	# strings
	assert Filter( 'name', 'unknown' )( m[1] )
	assert Filter( 'name', 'UNKNOWN' )( m[1] )
	assert not Filter( 'name', 'somewhere' )( m[1] )
	assert Filter( 'name', '^Unknown.*$', regex=True )( m[1] )
	assert not Filter( 'name', '^Unknown.*$' )( m[1] )

	# enum type
	assert Filter( 'type', ActivityTypes.xcski  )( m[1] )
	assert Filter( 'type', 'xcski'  )( m[1] )
	assert not Filter( 'type', ActivityTypes.xcski )( m[2] )

	# uids
	assert Filter( 'uids', 'polar:1234567890' )( m[1] )
	assert not Filter( 'uids', 'polar:9999' )( m[1] )

	# field is
	assert Filter( 'calories', 2904 )( m[2] )
	assert not Filter( 'calories', 100 )( m[2] )

	# field in range
	assert Filter( 'heartrate', (140, 160) )( m[2] )
	assert not Filter( 'heartrate', (160, 200) )( m[2] )

	# datetime ranges
	assert Filter( 'time', (datetime( 2012, 1, 1, tzinfo=UTC ), datetime( 2012, 1, 12, tzinfo=UTC )) )( m[2] )

	# time_ranges
	assert Filter( 'time', time( 10, 40, 51 ) )( m[2] )
	assert Filter( 'time', (time( 10 ), time( 11 )) )( m[2] )

	# field exists, field value is not None/''/[]
	assert not Filter( 'name' )( m[1] )
	assert Filter( 'location_country' )( m[1] )
	assert Filter( 'location_city' )( m[1] )
	assert not Filter( 'location_place' )( m[1] )
	assert Filter( 'heartrate' )( m[1] )
	assert Filter( 'tags' )( m[1] )

@mark.db( template='default', inmemory=True )
def test_filters_on_list( db ):
	_all = db.activities.all()

	def flt( f: QueryLike ) -> List[int]:
		return ids( filter( f, _all ) )

	def flt_dbg( f: QueryLike ) -> List[int]:
		rval = []
		for a in _all:
			rval.extend( ids( filter( f, [a] ) ) )
		return rval

	assert flt( true() ) == [1, 2, 3, 4]
	assert flt( false() ) == []

	assert flt( Filter( 'id', 1 ) ) == [1]
	assert flt( Filter( 'id', 2 ) ) == [2]

	assert flt( Filter( 'name', 'run' ) ) == [3]

	assert flt( Filter( 'type', ActivityTypes.xcski ) ) == [1]

	assert flt( Filter( 'calories', 2904 ) ) == [2]

	assert flt( Filter( 'heartrate', (110, 150) ) ) == [2, 3, 4]
	assert flt( Filter( 'heartrate', (~maxsize, 140) ) ) == [3, 4]
	assert flt( Filter( 'heartrate', (140, maxsize) ) ) == [2, 3]

	assert flt( Filter( 'time', (datetime( 2021, 1, 10, tzinfo=UTC ), datetime( 2021, 1, 12, tzinfo=UTC )) ) ) == [4]
	assert flt( Filter( 'time', time( 12 ) ) ) == [4]
	assert flt( Filter( 'time', time( 12, 0, 0 ) ) ) == [4]
	assert flt( Filter( 'time', (time( 11 ), time( 13 )) ) ) == [4]

@mark.db( template='default', inmemory=True )
def test_prepared_filters( db ):
	_all = db.activities.all()

	def flt( *args, **kwargs ) -> List[int]:
		return ids( filter( parse( *args ), _all ) )

	assert flt( '1' ) == [1]
	assert flt( 'id:1' ) == [1]
	assert flt( 'id:1..4' ) == [1, 2, 3, 4]

	assert flt( 'name:run' ) == [3]
	assert flt( 'name:unknown' ) == [1, 4]

	assert flt( 'service:polar' ) == [1, 2]

	assert flt( 'calories:2904' ) == [2]

	assert flt( 'heartrate:110..150' ) == [2, 3, 4]
	assert flt( 'heartrate:..140' ) == [3, 4]
	assert flt( 'heartrate:130..' ) == [2, 3, 4]

	assert flt( 'date:2021-01-10..2021-01-12' ) == [4]

	assert flt( 'time:12' ) == [4]
	#assert flt( 'time:154810' ) == [11] # not allowed (yet?)
	assert flt( 'time:11..13' ) == [4]

# internal helpers

def _fday( year, month, day ):
	return dt( year, month, day ).floor( 'day' )

def _fmonth( year, month ):
	return dt( year, month, 15 ).floor( 'month' )

def _fyear( year ):
	return dt( year, 7, 15 ).floor( 'year' )

def _cday( year, month, day ):
	return dt( year, month, day ).ceil( 'day' )

def _cmonth( year, month ):
	return dt( year, month, 15 ).ceil( 'month' )

def _cyear( year ):
	return dt( year, 7, 15 ).ceil( 'year' )

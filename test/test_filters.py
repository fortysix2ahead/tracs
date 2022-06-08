
from typing import List

from arrow import Arrow as dt
from arrow import now
from datetime import datetime
from datetime import time
from tinydb.queries import QueryLike

from tracs.activity_types import ActivityTypes
from tracs.filters import false
from tracs.filters import invalid
from tracs.filters import parse
from tracs.filters import prepare
from tracs.filters import true
from tracs.filters import Filter

from .fixtures import db_default_inmemory
from .helpers import ids

def test_predefined_filters():
	assert false().callable is not None
	assert false().valid == True

	assert true().callable is not None
	assert true().valid == True

	assert invalid().callable is not None
	assert invalid().valid == False

def test_parse():
	assert parse( '1000' ) == Filter( field=None, value=1000 ) # number is assumed to be an id or a raw_id

	assert parse( 'id:1000' ) == Filter( 'id', 1000 )
	assert parse( '^id:1000' ) == Filter( 'id', 1000, negate=True )
	assert parse( 'id:' ) == Filter( 'id' )
	assert parse( 'id:1000..' ) == Filter( 'id', range_from=1000 )
	assert parse( 'id:..1010' ) == Filter( 'id', range_to=1010 )
	assert parse( 'id:1000..1010' ) == Filter( 'id', range_from=1000, range_to=1010 )

	assert parse( 'id:1000,1001,1002' ) == Filter( 'id', sequence=[1000, 1001, 1002] )

	# service/source are special fields and shall be translated to _classifier
	assert parse( 'classifier:polar' ) == Filter( '_classifier', 'polar' )
	assert parse( 'service:polar' ) == Filter( '_classifier', 'polar' )
	assert parse( 'source:polar' ) == Filter( '_classifier', 'polar' )

	# again, this is special: this is an uid and should be treated as raw_id:<number>
	assert parse( 'polar:123456' ) == Filter( 'raw_id', 123456, 'polar' )

	# not sure if we should allow this: fields which only exist in a classified activity
	assert parse( 'polar.eventType:exercise' ) == Filter( 'eventType', 'exercise', 'polar' )

	assert parse( 'raw_id:123456' ) == Filter( 'raw_id', 123456 )

	assert parse( 'name:Run1' ) == Filter( 'name', 'Run1' )
	assert parse( 'name:run,hike,walk' ) == Filter( 'name', sequence=['run', 'hike', 'walk'] )

	assert parse( 'type:run' ) == Filter( 'type', 'run' )

	assert parse( 'distance:5000' ) == Filter( 'distance', int( 5000 ) )
	assert parse( 'distance:5500.55' ) == Filter( 'distance', 5500.55 )
	assert parse( 'distance:5000..6000' ) == Filter( 'distance', range_from=5000, range_to=6000 )
	assert parse( 'distance:5000..' ) == Filter( 'distance', range_from=5000 )
	assert parse( 'distance:..6000' ) == Filter( 'distance', range_to=6000 )
	assert parse( 'distance:5000.0..6000.0' ) == Filter( 'distance', range_from=5000.0, range_to=6000.0 )
	assert parse( 'distance:5000.0..' ) == Filter( 'distance', range_from=5000.0 )
	assert parse( 'distance:..6000.0' ) == Filter( 'distance', range_to=6000.0 )
	assert parse( 'distance:' ) == Filter( 'distance' )

	assert parse( 'date:2020' ) == Filter( 'date', range_from=_fyear( 2020 ), range_to=_cyear( 2020 ) )
	assert parse( 'date:..2020' ) == Filter( 'date', range_to=_cyear( 2020 ) )
	assert parse( 'date:2020..' ) == Filter( 'date', range_from=_fyear( 2020 ) )
	assert parse( 'date:2020..2021' ) == Filter( 'date', range_from=_fyear( 2020 ), range_to=_cyear( 2021 ) )

	assert parse( 'date:2020-05' ) == Filter( 'date', range_from=_fmonth( 2020, 5 ), range_to=_cmonth( 2020, 5 ) )
	assert parse( 'date:2020-05..' ) == Filter( 'date', range_from=_fmonth( 2020, 5 ) )
	assert parse( 'date:..2020-05' ) == Filter( 'date', range_to=_cmonth( 2020, 5 ) )
	assert parse( 'date:2020-02..2020-05' ) == Filter( 'date', range_from=_fmonth( 2020, 2 ), range_to=_cmonth( 2020, 5 ) )

	assert parse( 'date:2020-05-17' ) == Filter( 'date', range_from=_fday( 2020, 5, 17 ), range_to=_cday( 2020, 5, 17 ) )
	assert parse( 'date:2020-05-17..' ) == Filter( 'date', range_from=_fday( 2020, 5, 17 ) )
	assert parse( 'date:..2020-05-17' ) == Filter( 'date', range_to=_cday( 2020, 5, 17 ) )
	assert parse( 'date:2020-05-04..2020-05-17' ) == Filter( 'date', range_from=_fday( 2020, 5, 4 ), range_to=_cday( 2020, 5, 17 ) )

#	assert parse( 'date:latest' ) == Filter( 'date', value='latest' )
#	assert parse( 'date:lastweek' ) == (None, 'time', 'lastweek', None, None, False)

	n = now()
	assert parse( 'date:today' ) == Filter( 'date', range_from=n.floor( 'day' ), range_to=n.ceil( 'day' ) )
	assert parse( 'date:thisweek' ) == Filter( 'date', range_from=n.floor( 'week' ), range_to=n.ceil( 'week' ) )
	assert parse( 'date:thismonth' ) == Filter( 'date', range_from=n.floor( 'month' ), range_to=n.ceil( 'month' ) )
	assert parse( 'date:thisquarter' ) == Filter( 'date', range_from=n.floor( 'quarter' ), range_to=n.ceil( 'quarter' ) )
	assert parse( 'date:thisyear' ) == Filter( 'date', range_from=n.floor( 'year' ), range_to=n.ceil( 'year' ) )

	ns = now().shift( days=-6 )
	assert parse( 'date:last7days' ) == Filter( 'date', range_from=ns.floor( 'day' ), range_to=n.ceil( 'day' ) )

	ns = now().shift( days=-29 )
	assert parse( 'date:last30days' ) == Filter( 'date', range_from=ns.floor( 'day' ), range_to=n.ceil( 'day' ) )

	ns = now().shift( days=-59 )
	assert parse( 'date:last60days' ) == Filter( 'date', range_from=ns.floor( 'day' ), range_to=n.ceil( 'day' ) )

	ns = now().shift( days=-89 )
	assert parse( 'date:last90days' ) == Filter( 'date', range_from=ns.floor( 'day' ), range_to=n.ceil( 'day' ) )

	ns = now().shift( days=-1 )
	assert parse( 'date:yesterday' ) == Filter( 'date', range_from=ns.floor( 'day' ), range_to=ns.ceil( 'day' ) )
	ns = now().shift( weeks=-1 )
	assert parse( 'date:lastweek' ) == Filter( 'date', range_from=ns.floor( 'week' ), range_to=ns.ceil( 'week' ) )
	ns = now().shift( months=-1 )
	assert parse( 'date:lastmonth' ) == Filter( 'date', range_from=ns.floor( 'month' ), range_to=ns.ceil( 'month' ) )
	ns = now().shift( months=-3 )
	assert parse( 'date:lastquarter' ) == Filter( 'date', range_from=ns.floor( 'quarter' ), range_to=ns.ceil( 'quarter' ) )
	ns = now().shift( years=-1 )
	assert parse( 'date:lastyear' ) == Filter( 'date', range_from=ns.floor( 'year' ), range_to=ns.ceil( 'year' ) )

	# exact times
	assert parse( 'time:15' ) == Filter( 'time', value=time( 15 ) )
	assert parse( 'time:15:00' ) == Filter( 'time', value=time( 15, 0 ) )
	assert parse( 'time:15:00:07' ) == Filter( 'time', value=time( 15, 0, 7 ) )

	# time keywords
	assert parse( 'time:morning' ) == Filter( 'time', range_from=time( 6 ), range_to=( time( 11 ) ) ) # 06 to 11
	assert parse( 'time:noon' ) == Filter( 'time', range_from=time( 11 ), range_to=( time( 13 ) ) ) # 11 to 13
	assert parse( 'time:afternoon' ) == Filter( 'time', range_from=time( 13 ), range_to=( time( 18 ) ) ) # 13 to 18
	assert parse( 'time:evening' ) == Filter( 'time', range_from=time( 18 ), range_to=( time( 22 ) ) ) # 18 to 22
	assert parse( 'time:night' ) == Filter( 'time', range_from=time( 22 ), range_to=( time( 6 ) ) ) # 22 to 06

	# time ranges
	assert parse( 'time:15..17' ) == Filter( 'time', range_from=time( 15 ), range_to=time( 17 ) )
	assert parse( 'time:..17' ) == Filter( 'time', range_to=time( 17 ) )
	assert parse( 'time:15..' ) == Filter( 'time', range_from=time( 15 ) )
	assert parse( 'time:15:00..17:00' ) == Filter( 'time', range_from=time( 15 ), range_to=time( 17 ) )
	assert parse( 'time:15:00:05..17:00:07' ) == Filter( 'time', range_from=time( 15, 0, 5 ), range_to=time( 17, 0, 7 ) )

def test_filters_on_activities( db_default_inmemory ):
	db, json = db_default_inmemory
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

	# has_id
	assert Filter( value=1 )( m[1] )
	assert not Filter( value=1, negate=True )( m[1] )
	assert not Filter( value=1 )( m[2] )
	assert Filter( value=1, negate=True )( m[2] )

	# field_is equal to value
	assert Filter( 'id', 1 )( m[1] )
	assert not Filter( 'id', 2 )( m[1] )

	# has_raw_id
	assert Filter( value=1001 )( m[11] )
	assert Filter( value=2002 )( m[12] )
	assert Filter( value=3003 )( m[13] )
	assert Filter( value=4004 )( m[14] )
	assert Filter( value=12345600 )( m[20] )
	assert Filter( value=20200101010101 )( m[30] )

	# field_match
	assert Filter( 'name', 'run' )( m[20] )
	assert not Filter( 'name', 'walk' )( m[20] )

	# enum type
	assert Filter( 'type', ActivityTypes.xcski  )( m[1] )
	assert not Filter( 'type', ActivityTypes.xcski )( m[2] )

	# service
	assert Filter( 'classifier', 'polar' )( m[2] )
	assert Filter( 'service', 'strava' )( m[3] )
	assert Filter( 'source', 'waze' )( m[4] )
	assert not Filter( 'service', 'strava' )( m[2] )
	assert not Filter( 'service', 'waze' )( m[2] )

	# service of group activities
	assert Filter( 'service', 'polar' )( m[1] )
	assert Filter( 'service', 'strava' )( m[1] )
	assert Filter( 'service', 'waze' )( m[1] )

	# field is
	assert Filter( 'calories', 2904 )( m[2] )
	assert not Filter( 'calories', 100 )( m[2] )

	# field in range
	assert Filter( 'heartrate', range_from=80, range_to=90 )( m [40] )
	assert Filter( 'heartrate', range_from=110, range_to=150 )( m[41] )
	assert Filter( 'heartrate', range_to=130 )( m[40] )
	assert Filter( 'heartrate', range_from=110 )( m[41] )

	# field in list
	assert Filter( 'id', [1, 2, 3] )( m[1] )
	assert not Filter( 'id', [2, 3] )( m[1] )

	# datetime in range
	assert Filter( 'time', range_from=datetime( 2020, 1, 10 ), range_to=datetime( 2020, 1, 12 ) )( m[30] )

	# time_is
	assert Filter( 'time', value=time( 12, 0, 0 ) )( m[30] )
	assert Filter( 'time', value=time( 15, 48, 10 ) )( m[11] )

	# time in range
	assert Filter( 'time', range_from=time( 11 ), range_to=time( 13 ) )( m[4] )

	# field exists, field value is not None/''/[]
	assert Filter( 'name' )( m[1] )
	assert not Filter( 'empty_field' )( m[1] )
	assert not Filter( 'location_country' )( m[1] )
	assert not Filter( 'location_city' )( m[1] )
	assert not Filter( 'tags' )( m[1] )

def test_filters_on_list( db_default_inmemory ):
	db, json = db_default_inmemory
	_all = db.activities.all()

	def flt( f: QueryLike ) -> List[int]:
		return ids( filter( f, _all ) )

	def flt_dbg( f: QueryLike ) -> List[int]:
		rval = []
		for a in _all:
			rval.extend( ids( filter( f, [a] ) ) )
		return rval

	def fltp( f: Filter ) -> List[int]:
		return ids( filter( prepare( f ), _all ) )

	assert flt( true() ) == [1, 2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]
	assert flt( false() ) == []

	assert flt( Filter( value = 1 ) ) == [1]
	assert flt( Filter( 'id', 1 ) ) == [1]
	assert flt( Filter( 'id', 2 ) ) == [2]

	assert flt( Filter( value=1001 ) ) == [11]

	assert flt( Filter( value=2002 ) ) == [12]
	assert flt( Filter( value=3003 ) ) == [13]
	assert flt( Filter( value=4004 ) ) == [14]
	assert flt( Filter( value=12345600 ) ) == [20]
	assert flt( Filter( value=20200101010101 ) ) == [30]

	assert flt( Filter( 'name', 'run' ) ) == [3, 20]

	assert flt( Filter( 'type', ActivityTypes.xcski ) ) == [1, 3, 20]

	assert flt( Filter( 'service', 'polar' ) ) == [1, 2, 11, 12, 13, 14, 41, 51, 52]
	assert flt( Filter( 'service', 'strava' ) ) == [1, 3, 20, 40, 53, 54, 55]
	assert flt( Filter( 'service', 'waze' ) ) == [1, 4, 30]

	assert flt( Filter( 'calories', 2904 ) ) == [2]
	assert flt( Filter( 'calories', 456 ) ) == [11]

	assert flt( Filter( 'heartrate', range_from=80, range_to=90 ) ) == [40]
	assert flt( Filter( 'heartrate', range_from=110, range_to=150 ) ) == [41]
	assert flt( Filter( 'heartrate', range_to=130 ) ) == [40, 41]
	assert flt( Filter( 'heartrate', range_from=110 ) ) == [3, 41]
	# assert flt( Filter( 'heartrate' ) ) == [3, 40, 41]

	assert flt( Filter( 'id', [1, 2, 3] ) ) == [1, 2, 3]

	assert flt( Filter( 'time', range_from=datetime( 2020, 1, 10 ), range_to=datetime( 2020, 1, 12 ) ) ) == [30]

	assert flt( Filter( 'time', time( 12 ) ) ) == [4, 30]
	assert flt( Filter( 'time', time( 15, 48, 10 ) ) ) == [11]

	assert flt( Filter( 'time', range_from=time( 11 ), range_to=time( 13 ) ) ) == [4, 30, 40, 41]

	#assert flt( is_empty( 'empty_field' ) ) == [1, 2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]
	#assert flt( is_empty( 'nonempty_field' ) ) == [2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]
	#assert flt( is_empty( 'null_field' ) ) == [1, 2, 3, 4, 11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	#assert flt( is_ungrouped() ) == [11, 12, 13, 14, 20, 30, 40, 41, 51, 52, 53, 54, 55]

	#assert flt( is_group() ) == [1]

def test_prepared_filters( db_default_inmemory ):
	db, json = db_default_inmemory
	_all = db.activities.all()

	def flt( *args, **kwargs ) -> List[int]:
		f = parse( *args )
		return ids( filter( f, _all ) )

	assert flt( '1' ) == [1]
	assert flt( 'id:1' ) == [1]
	assert flt( 'id:1..4' ) == [1, 2, 3]

	assert flt( 'name:run' ) == [3, 20]
	assert flt( 'name:drive' ) == [30]

	#assert flt( 'service:waze' ) == [1, 4, 30]

	assert flt( 'calories:2904' ) == [2]

	assert flt( 'heartrate:110..150' ) == [41]
	assert flt( 'heartrate:..130' ) == [40, 41]
	assert flt( 'heartrate:110..' ) == [3, 41]

	#assert flt( 'date:2020-01-10..2020-01-12' ) == [30]

	assert flt( 'time:12' ) == [4, 30]
	#assert flt( 'time:154810' ) == [11] # not allowed (yet?)
	assert flt( 'time:11..13' ) == [4, 30, 40, 41]

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

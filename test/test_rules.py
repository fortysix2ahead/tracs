
from datetime import datetime, time
from re import match
from typing import cast

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from pytest import mark, raises
from rule_engine import Context
from rule_engine import EvaluationError
from rule_engine import resolve_attribute
from rule_engine import Rule
from rule_engine import RuleSyntaxError
from rule_engine import SymbolResolutionError

from tracs.activity import Activity, ActivityPart
from tracs.activity_types import ActivityTypes
from tracs.plugins.polar import Polar
from tracs.plugins.rule_extensions import TIME_FRAMES as TIME_FRAMES_EXT
from tracs.rules import DATE_PATTERN
from tracs.rules import FUZZY_DATE_PATTERN
from tracs.rules import FUZZY_TIME_PATTERN
from tracs.rules import INT_LIST
from tracs.rules import INT_PATTERN
from tracs.rules import KEYWORD_PATTERN
from tracs.rules import LIST_PATTERN
from tracs.rules import normalize
from tracs.rules import parse_date_range_as_str
from tracs.rules import parse_rule
from tracs.rules import RANGE_PATTERN
from tracs.rules import RULE_PATTERN
from tracs.rules import TIME_PATTERN

NOW = datetime.utcnow()
ATTRIBUTE_CONTEXT = Context(resolver=resolve_attribute)

TIME_FRAMES_EXT_FROM_PLUGIN = TIME_FRAMES_EXT # this is to make sure the rule_extensions plugin is loaded

A1 = Activity(
	id=1000,
	name="Berlin",
	description="Morning Run in Berlin",
	type=ActivityTypes.run,
	time=datetime( 2023, 1, 13, 10, 0, 42, tzinfo=UTC ),
	localtime=datetime( 2023, 1, 13, 10, 0, 42, tzinfo=UTC ).astimezone( tzlocal() ),
	heartrate=160,
	uids=['polar:123456', 'strava:123456']
)

d2 = {
	'heartrate': 180,
	'time': datetime.utcnow(),
	'tags': ['morning', 'salomon', 'tired'],
	'uids': ['polar:1234', 'strava:3456']
}

a2 = Activity(
	heartrate=180,
	time=datetime.utcnow(),
	tags=['morning', 'salomon', 'tired'],
	uids=['polar:1234', 'strava:3456']
)

def test_rule_engine():
	# plain case does not work with classes, only with dictionaries
	with raises( SymbolResolutionError ):
		assert Rule( 'heartrate == 180' ).matches( a2 )
	assert Rule( 'heartrate == 180' ).matches( d2 )
	assert Rule( 'heartrate == 180', context=ATTRIBUTE_CONTEXT ).matches( a2 )
	assert not Rule( 'heartrate_max == 180', context=ATTRIBUTE_CONTEXT ).matches( a2 )

	# how to get around a SymbolResolutionError:
	context = Context( default_value=None )
	rule = Rule( 'year == 2023', context=context )
	assert not rule.matches( a2 )

	# how to use a custom resolver
	def resolve_year( thing, name ):
		if name == 'year':
			return cast( Activity, thing ).time.year
		elif name == 'classifiers' and type( thing ) is tuple:
			return list( map( lambda s: s.split( ':', 1 )[0], thing ) )
		else:
			return resolve_attribute( thing, name )

	context = Context( default_value=None, resolver=resolve_year )
	assert Rule( 'heartrate == 180', context=context ).matches( a2 )
	assert Rule( 'year == 2023', context=context ).matches( a2 )
	assert Rule( 'heartrate == 180 and year == 2023', context=context ).matches( a2 )
	assert not Rule( 'heartrate == 170 and year == 2023', context=context ).matches( a2 )

	assert Rule( '"tired" in tags', context=context ).matches( a2 )
	assert not Rule( '"evening" in tags', context=context ).matches( a2 )

	assert Rule( '"polar:1234" in uids', context=context ).matches( a2 )
	assert not Rule( '"polar" in uids', context=context ).matches( a2 )
	assert Rule( '"polar" in uids.classifiers', context=context ).matches( a2 )

def test_rule_pattern():
	# special cases

	# numbers are allowed and are treated as ids
	assert match( INT_PATTERN, '1000' )

	# list are comma-separated and need to contain more than one element
	assert match( LIST_PATTERN, '100,101')
	assert match( LIST_PATTERN, '100,101,102')
	assert match( LIST_PATTERN, 'a,b,c')
	assert not match( LIST_PATTERN, '100')
	assert not match( LIST_PATTERN, '100,101,102,')

	assert INT_LIST.match( '1000,1001,1002' )
	assert not INT_LIST.match( '1000,1001,1002,' )

	# ranges are separated by two dots, where start and end might be missing
	assert match( RANGE_PATTERN, '1000..1002' )
	assert match( RANGE_PATTERN, '1000..' )
	assert match( RANGE_PATTERN, '..1002' )
	assert match( RANGE_PATTERN, '100.4..100.9' )
	assert match( RANGE_PATTERN, '2020-01-01..2020-06-30' )
	assert match( RANGE_PATTERN, '10:00:00..11:00:00' )

	# dates always contain year, month and day
	assert match( DATE_PATTERN, '2022-03-13' )
	assert not match( DATE_PATTERN, '2022' )
	assert not match( DATE_PATTERN, '2022-03' )

	# fuzzy dates may omit month and day and are treated as ranges
	assert match( FUZZY_DATE_PATTERN, '2022' ) # beware: this is also a number!
	assert match( FUZZY_DATE_PATTERN, '2022-03' )
	assert match( FUZZY_DATE_PATTERN, '2022-03-13' )

	# same is true for times: always contain hours, minutes and seconds
	assert match( TIME_PATTERN, '13:10:42' )
	assert not match( TIME_PATTERN, '13' )
	assert not match( TIME_PATTERN, '13:10' )

	# fuzzy times are also treated as ranges
	assert match( FUZZY_TIME_PATTERN, '13' )
	assert match( FUZZY_TIME_PATTERN, '13:10' )
	assert match( FUZZY_TIME_PATTERN, '13:10:42' )

	# keywords must begin with a letter and may contain letters, numbers, dashes und underscores

	assert match( KEYWORD_PATTERN, 'polar' )
	assert match( KEYWORD_PATTERN, 'polar_2022' )
	assert match( KEYWORD_PATTERN, 'polar-2022' )
	assert match( KEYWORD_PATTERN, 'Polar22' )
	assert not match( KEYWORD_PATTERN, '1Polar22' )

	# normal expressions

	# empty value is allowed
	assert match( RULE_PATTERN, 'id:' )

	assert match( RULE_PATTERN, 'id:1000' )
	assert match( RULE_PATTERN, 'ID:1000' )

	assert match( RULE_PATTERN, 'id:1000,1001,1002' )
	assert match( RULE_PATTERN, 'id:1000..1002' )

	assert match( RULE_PATTERN, 'date:2020-01-15..2021-09-01' )
	assert match( RULE_PATTERN, 'date:2020..2021-09' )

	assert match( RULE_PATTERN, 'id=1000' )
	assert match( RULE_PATTERN, 'id==1000' )
	assert match( RULE_PATTERN, 'id!=1000' )
	assert match( RULE_PATTERN, 'id>1000' )
	assert match( RULE_PATTERN, 'id>=1000' )
	assert match( RULE_PATTERN, 'id<1000' )
	assert match( RULE_PATTERN, 'id<=1000' )

	assert match( RULE_PATTERN, 'name:berlin' )
	assert match( RULE_PATTERN, 'name=Berlin' )
	assert match( RULE_PATTERN, 'name="Morning Run"' )
	assert match( RULE_PATTERN, 'name!="Morning Run"' )
	assert match( RULE_PATTERN, 'name=~"^.*Run$"' )
	assert match( RULE_PATTERN, 'name!~"^.*Run$"' )

	assert match( RULE_PATTERN, 'type:run,hike,walk' )

# def test_rule_resource_pattern():
# 	assert match( RESOURCE_PATTERN, 'polar:1000#1' )
# 	assert match( RESOURCE_PATTERN, 'polar:1000#gpx' )
# 	# assert match( RESOURCE_PATTERN, 'polar:1000?1001.gpx' )
# 	assert match( RESOURCE_PATTERN, 'polar:1001#application/xml+gpx' )
# 	assert match( RESOURCE_PATTERN, 'polar:1001#application/xml+gpx-polar' )

@mark.context( library='empty', config='empty', cleanup=True )
@mark.service( cls=Polar )
def test_normalize( service ):
	# numbers from 2000 to current year are treated as years, otherwise
	current_year = datetime.now().year
	assert normalize( '1000' ) == 'id == 1000'
	assert normalize( '1999' ) == 'id == 1999'
	assert normalize( '2000' ) == 'year == 2000'
	assert normalize( str( current_year ) ) == f'year == {current_year}'
	assert normalize( str( current_year + 1 ) ) == f'id == {current_year + 1}'

	# integer ranges can contain missing bounds and are treated as ids, bounds are inclusive
	assert normalize( '1000..1003' ) == 'id >= 1000 and id <= 1003'
	assert normalize( '1000..' ) == 'id >= 1000'
	assert normalize( '..1003' ) == 'id <= 1003'

	# integer lists are treated as id lists
	assert normalize( '100,101,102' ) == 'id in [100,101,102]'

	# there should be keywords for each registered service (and others)
	assert isinstance( service, Polar ) # after creating a polar service instance there should be a polar keyword registered
	assert normalize( 'polar' ) == f'"polar" in classifiers'
	# unknown keywords result in an error
	with raises( RuleSyntaxError ):
		normalize( 'unknown_keyword' )

	# todo: more tests with the normal rule engine syntax need to go in here
	# single equal is allowed and will be expanded to double
	assert normalize( 'id=1000' ) == 'id == 1000'

	# normal expressions are just passed through
	assert normalize( 'id!=1000' ) == 'id != 1000'

	# colon expressions
	assert normalize( 'id:' ) == 'id == null' # missing values is treated as null
	assert normalize( 'id:1000' ) == 'id == 1000' # normal case: expand to equals
	assert normalize( 'flag:true' ) == 'flag == true' and normalize( 'flag:false' ) == 'flag == false' # boolean flags
	assert normalize( 'name:"afternoon run"' ) == 'name != null and "afternoon run" in name.as_lower' # allow search-like string values
	assert normalize( 'name:afternoon' ) == 'name != null and "afternoon" in name.as_lower' # same for unquoted strings

	# custom normalizer handling
	assert normalize( 'type:run' ) == 'type.name == "run"'

def test_parse():
	assert (r := parse_rule( 'id=1000' ))
	assert r.evaluate( Activity( id=1000 ) )

	assert (r := parse_rule( 'id!=1000' ))
	assert r.evaluate( Activity( id=1001 ) )

	with raises( EvaluationError ):
		assert (r := parse_rule( 'id=~1000' )) # wrong operator, parsing fails
		r.evaluate( Activity( id=1000 ) )

	assert (r := parse_rule( 'unknown:1000' )) # parsing unknown fields is ok
	with raises( SymbolResolutionError ):
		assert r.evaluate( Activity( id=1000 ) ) # evaluating is not ok -> error

def test_evaluate():
	al = [
		Activity(
			id = 1000,
			name = 'Berlin',
		),
		Activity(
			id = 1001,
		)
	]

	assert parse_rule( 'id=1000' ).evaluate( A1 )
	assert parse_rule( f'year={NOW.year}' ).evaluate( A1 )
	assert parse_rule( 'classifier:polar' ).evaluate( A1 )
	assert parse_rule( 'thisyear' ).evaluate( A1 )

	assert parse_rule( 'name=Berlin' ).evaluate( A1 )
	assert not parse_rule( 'name=berlin' ).evaluate( A1 )

	assert parse_rule( 'description="Morning Run in Berlin"' ).evaluate( A1 )
	assert not parse_rule( 'description="morning run in berlin"' ).evaluate( A1 )

	assert parse_rule( 'name:berlin' ).evaluate( A1 )
	assert not parse_rule( 'name:hamburg' ).evaluate( A1 )
	assert parse_rule( 'description:"morning run"' ).evaluate( A1 )

	assert list( parse_rule( 'name:berlin' ).filter( al ) ) == [ al[0] ]
	assert not parse_rule( 'location_place:hamburg' ).evaluate( A1 )

	assert list( parse_rule( 'name:' ).filter( al ) ) == [ al[1] ]

	with raises( SymbolResolutionError ):
		parse_rule( 'invalid=1000' ).evaluate( A1 )

	# RuleSyntaxError should never happen ...

def test_evaluate_multipart():
	p1 = ActivityPart( uids=['polar:101' ], gap=time( 0, 0, 0 ) )
	p2 = ActivityPart( uids=['polar:102', 'strava:102' ], gap=time( 1, 0, 0 ) )
	a = Activity( parts=[ p1, p2 ] )

	assert a.multipart
	assert parse_eval( 'multipart=true', a )
	assert not parse_eval( 'multipart=false', a )
	assert parse_eval( 'multipart:true', a )
	assert not parse_eval( 'multipart:false', a )

def test_type():
	# assert parse_eval( 'type=run', A1 ) # todo: support this?
	assert parse_eval( 'type:run', A1 )
	assert parse_eval( 'type:Run', A1 )

def test_list():
	assert parse_eval( '1000,1001,1002', A1 )
	assert not parse_eval( '100,101,102', A1 )

def test_range():
	assert not parse_eval( 'id=999..1001', A1 )
	assert parse_eval( 'id:999..1001', A1 )
	assert parse_eval( 'id:999.0..1001', A1 ) # mixed int/float works as well
	assert parse_eval( 'id:999..', A1 )
	assert parse_eval( 'id:..1001', A1 )
	assert not parse_eval( 'id:800..900', A1 )
	assert not parse_eval( 'id:..900', A1 )
	assert not parse_eval( 'id:1001..', A1 )

	assert parse_eval( 'heartrate:100.0..200.0', A1 )

def test_date_time():
	assert parse_eval( 'date=2023-01-13', A1 )
	assert parse_eval( 'date:2023', A1 )
	assert not parse_eval( 'date:2022', A1 )
	assert parse_eval( 'date:2023-01', A1 )
	assert not parse_eval( 'date:2022-01', A1 )
	assert parse_eval( 'date:2023-01-13', A1 )
	assert not parse_eval( 'date:2022-01-13', A1 )

	assert parse_eval( 'date:2022..2023', A1 )
	assert parse_eval( 'date:2022..', A1 )
	assert parse_eval( 'date:..2023', A1 )
	assert parse_eval( 'date:2023-01-12..2023-02', A1 )

	# assert parse_eval( 'time=10:00:42', A1 )

def test_parse_date_range():

	assert parse_date_range_as_str( '2022..2023' ) == ('2022-01-01', '2023-12-31')
	assert parse_date_range_as_str( '2022..' ) == ('2022-01-01', '9999-12-31')
	assert parse_date_range_as_str( '..2023' ) == ('0001-01-01', '2023-12-31')

	assert parse_date_range_as_str( '2022-03..2022-03' ) == ('2022-03-01', '2022-03-31')
	assert parse_date_range_as_str( '..2022-03' ) == ('0001-01-01', '2022-03-31')
	assert parse_date_range_as_str( '2022-03..' ) == ('2022-03-01', '9999-12-31')

	assert parse_date_range_as_str( '2022-03-15..2022-03-16' ) == ('2022-03-15', '2022-03-16')
	assert parse_date_range_as_str( '..2022-03-16' ) == ('0001-01-01', '2022-03-16')
	assert parse_date_range_as_str( '2022-03-15..' ) == ('2022-03-15', '9999-12-31')

# helper

def parse_eval( rule: str, thing: Activity ) -> bool:
	return parse_rule( rule ).evaluate( thing )

from attrs import asdict, evolve
from dateutil.tz import tzlocal
from pytest import mark, raises
from rule_engine import __version__ as rule_engine_version, Context, DataType, EvaluationError

from test.objects import COMPLETE_ACTIVITY as a
from tracs.activity_types import ActivityTypes
from tracs.core import Metadata
from tracs.plugins.keywords import TIME_FRAMES as TIME_FRAMES_EXT
from tracs.rules import *
from tracs.uid import UID

log = getLogger( __name__ )

NOW = datetime.now( UTC )
ATTRIBUTE_CONTEXT = Context( resolver=resolve_attribute )

TIME_FRAMES_EXT_FROM_PLUGIN = TIME_FRAMES_EXT # this is to make sure the rule_extensions plugin is loaded

A1 = Activity(
	id=1000,
	name="Berlin",
	description="Morning Run in Berlin",
	type=ActivityTypes.run,
	starttime=datetime( 2023, 1, 13, 10, 0, 42, tzinfo=UTC ),
	starttime_local=datetime( 2023, 1, 13, 10, 0, 42, tzinfo=UTC ).astimezone( tzlocal() ),
	heartrate=160,
	metadata=Metadata(
		members=UID.from_strs( ['polar:123456', 'strava:123456'] )
	)
)

d2 = {
	'heartrate': 180,
	'time': datetime.now( UTC ),
	'tags': ['morning', 'salomon', 'tired'],
	'uids': ['polar:1234', 'strava:3456']
}

a2 = Activity(
	heartrate=180,
	starttime=datetime( 2023, 11, 11, 10, 0, 42, tzinfo=UTC ),
	tags=['morning', 'salomon', 'tired'],
	metadata = Metadata(
		members=UID.from_strs( ['polar:1234', 'strava:3456'] )
	)
)

@define
class SampleEquipment:

	equipment: List[str] = field( default=[ 'shoes' ] )

@define
class SampleActivity:

	equipment: SampleEquipment = field( factory=SampleEquipment )
	id: int = field( default=0 )
	heartrate: int = field( default=180 )
	heartrate_max: int = field( default=220 )
	heartrate_str: str = field( default='180' )
	name: str = field( default='sample' )
	tags: List[str] = field( default=[ 'tired' ] )

# don't know yet what to do with the schema

SampleActivitySchema = DataType.OBJECT( 'SampleActivity',attributes={
		'id': DataType.FLOAT,
		'name': DataType.STRING,
	},
)

# only works with dataclasses
# SampleActivityType = DataType.OBJECT.from_dataclass( 'SampleActivity', SampleActivity )

#
class CustomBuiltinsContext( Context ):

	def __init__( self, *args, **kwargs ):
		# call the parent class's __init__ method first to set the default_timezone attribute
		super( CustomBuiltinsContext, self ).__init__( default_value=None, resolver=resolve_attribute )

		self.builtins = Builtins.from_defaults({
			'uppr': lambda v: v.upper(),
			'version': rule_engine_version },
			timezone=self.default_timezone,
      )

# test case to learn about rule engine capabilities

@mark.unit
def test_rule_engine():
	# sample instance
	a = SampleActivity()

	# plain case does not work with classes, only with dictionaries
	with raises( SymbolResolutionError ):
		assert Rule( 'heartrate == 180' ).matches( a )
	assert Rule( 'heartrate == 180' ).matches( asdict( a ) )

	# apply custom context to make it work with dataclasses
	assert Rule( 'heartrate == 180', context=ATTRIBUTE_CONTEXT ).matches( a )
	assert not Rule( 'heartrate_max == 180', context=ATTRIBUTE_CONTEXT ).matches( a )

	# how to get around a SymbolResolutionError:
	context = Context( default_value=None )
	rule = Rule( 'year == 2023', context=context )
	assert not rule.matches( a )

	# how to use a custom resolver
	def resolve_year( thing, name ):
		if name == 'year':
			return 2023
		else:
			return resolve_attribute( thing, name )

	context = Context( default_value=None, resolver=resolve_year )
	assert Rule( 'heartrate == 180', context=context ).matches( a )
	assert Rule( 'year == 2023', context=context ).matches( a )
	assert Rule( 'heartrate == 180 and year == 2023', context=context ).matches( a )
	assert not Rule( 'heartrate == 170 and year == 2023', context=context ).matches( a )

	# testing functions
	# this fails as heartrate_str is a string and cannot be compared to a number
	with raises( EvaluationError ):
		assert Rule( 'heartrate_str >= 180', context=context ).matches( a )
	# string comparison works
	assert Rule( 'heartrate_str == "180"', context=context ).matches( a )
	# conversion to float and compare to value, note that the preceding $ is necessary
	assert Rule( '$parse_float( heartrate_str ) >= 180', context=context ).matches( a )

	assert Rule( '"tired" in tags', context=context ).matches( a )
	assert not Rule( '"evening" in tags', context=context ).matches( a )

	# access sub objects via dot notation
	assert Rule( '"shoes" in equipment.equipment', context=context ).matches( a )

	# test custom context with extended builtins
	context = CustomBuiltinsContext( default_value=None )
	assert Rule( 'heartrate == 180', context=context ).matches( a )
	assert Rule( '$version == "5.0.0"', context=context ).matches( a )
	assert Rule( '$uppr( name ) == "SAMPLE"', context=context ).matches( a )

@mark.unit
def test_rule_pattern():
	# special cases

	# numbers are allowed and are treated as ids
	assert INT.fullmatch( '1000' )
	assert not INT.fullmatch( '1000..2000' )

	# lists are comma-separated and need to contain more than one element
	assert INT_LIST.fullmatch( '1000,1001,1002' )
	assert not INT_LIST.fullmatch( '1000' ) # not a list, at least two elements needed
	assert not INT_LIST.fullmatch( '1000,abc,1002,' ) # no int list
	assert not INT_LIST.fullmatch( '1000,1001,1002,' ) # trailing comma is not allowed

	assert LIST.fullmatch( '100,101,102' )
	assert LIST.fullmatch( '100,abc,102' )
	assert not LIST.fullmatch( '100' )
	assert not LIST.fullmatch( '100,101,102,' )

	# ranges are separated by two dots, where start and end might be missing
	assert INT_RANGE.fullmatch( '1000..1002' )

	assert RANGE.fullmatch( '1000..1002' )
	assert RANGE.fullmatch( '1000..' )
	assert RANGE.fullmatch( '..1002' )
	assert RANGE.fullmatch( '100.4..100.9' )
	assert RANGE.fullmatch( '2020-01-01..2020-06-30' )
	assert RANGE.fullmatch( '10:00:00..11:00:00' )

	# date ranges
	assert DATE_RANGE.fullmatch( '2020..2020' )
	assert DATE_RANGE.fullmatch( '2020-01..2020-06' )
	assert DATE_RANGE.fullmatch( '2020-01-01..2020-06-30' )
	assert DATE_RANGE.fullmatch( '2020..' )
	assert DATE_RANGE.fullmatch( '2020-01..' )
	assert DATE_RANGE.fullmatch( '2020-01-01..' )
	assert DATE_RANGE.fullmatch( '..2020' )
	assert DATE_RANGE.fullmatch( '..2020-06-30' )
	assert DATE_RANGE.fullmatch( '..2020-06' )

	# time ranges
	assert TIME_RANGE.fullmatch( '09..11' )
	assert TIME_RANGE.fullmatch( '09:05..11:05' )
	assert TIME_RANGE.fullmatch( '09:05:36..11:05:55' )
	assert TIME_RANGE.fullmatch( '09..' )
	assert TIME_RANGE.fullmatch( '09:05..' )
	assert TIME_RANGE.fullmatch( '09:05:36..' )
	assert TIME_RANGE.fullmatch( '..11' )
	assert TIME_RANGE.fullmatch( '..11:05' )
	assert TIME_RANGE.fullmatch( '..11:05:55' )

	# dates always contain year, month and day
	assert DATE.fullmatch( '2022-03-13' )
	assert not DATE.fullmatch( '2022' )
	assert not DATE.fullmatch( '2022-03' )

	# fuzzy dates may omit month and day and are treated as ranges
	assert FUZZY_DATE.fullmatch( '2022' ) # beware: this is also a number!
	assert FUZZY_DATE.fullmatch( '2022-03' )
	assert FUZZY_DATE.fullmatch( '2022-03-13' )

	# same is true for times: always contain hours, minutes and seconds
	assert TIME.fullmatch( '13:10:42' )
	assert not TIME.fullmatch( '13' )
	assert not TIME.fullmatch( '13:10' )

	# fuzzy times are also treated as ranges
	assert FUZZY_TIME.fullmatch( '13' )
	assert FUZZY_TIME.fullmatch( '13:10' )
	assert FUZZY_TIME.fullmatch( '13:10:42' )

	# keywords must begin with a letter and may contain letters, numbers, dashes und underscores

	assert KEYWORD.fullmatch( 'polar' )
	assert KEYWORD.fullmatch( 'polar_2022' )
	assert KEYWORD.fullmatch( 'polar-2022' )
	assert KEYWORD.fullmatch( 'Polar22' )
	assert not KEYWORD.fullmatch( '1Polar22' )

	# normal expressions

	# empty value is allowed
	assert RULE.fullmatch( 'id:' )

	assert RULE.fullmatch( 'id:1000' )
	assert RULE.fullmatch( 'ID:1000' )

	assert RULE.fullmatch( 'id:1000,1001,1002' )
	assert RULE.fullmatch( 'id:1000..1002' )

	assert RULE.fullmatch( 'date:2020-01-15..2021-09-01' )
	assert RULE.fullmatch( 'date:2020..2021-09' )

	assert RULE.fullmatch( 'id=1000' )
	assert RULE.fullmatch( 'id==1000' )
	assert RULE.fullmatch( 'id!=1000' )
	assert RULE.fullmatch( 'id>1000' )
	assert RULE.fullmatch( 'id>=1000' )
	assert RULE.fullmatch( 'id<1000' )
	assert RULE.fullmatch( 'id<=1000' )

	assert RULE.fullmatch( 'name:berlin' )
	assert RULE.fullmatch( 'name=Berlin' )
	assert RULE.fullmatch( 'name="Morning Run"' )
	assert RULE.fullmatch( 'name!="Morning Run"' )
	assert RULE.fullmatch( 'name=~"^.*Run$"' )
	assert RULE.fullmatch( 'name!~"^.*Run$"' )

	assert RULE.fullmatch( 'type:run,hike,walk' )

	# rule negation
	assert RULE.fullmatch( '^name:berlin' )

# def test_rule_resource_pattern():
# 	assert match( RESOURCE_PATTERN, 'polar:1000#1' )
# 	assert match( RESOURCE_PATTERN, 'polar:1000#gpx' )
# 	# assert match( RESOURCE_PATTERN, 'polar:1000?1001.gpx' )
# 	assert match( RESOURCE_PATTERN, 'polar:1001#application/xml+gpx' )
# 	assert match( RESOURCE_PATTERN, 'polar:1001#application/xml+gpx-polar' )

@mark.unit
def test_normalize( parser ):
	p = parser

	# numbers from 2000 to current year are treated as years, otherwise
	assert p.normalize( '2020' ) == 'id == 2020'

	# integer ranges can contain missing bounds and are treated as ids, bounds are inclusive
	assert p.normalize( '1000..1003' ) == 'id >= 1000 and id <= 1003'
	assert p.normalize( '1000..' ) == 'id >= 1000'
	assert p.normalize( '..1003' ) == 'id <= 1003'

	# integer lists are treated as id lists
	assert p.normalize( '100,101,102' ) == 'id in [100,101,102]'

	# there should be keywords for each registered service (and others)
#	assert 'polar' in p.keywords
#	assert p.normalize( 'polar' ) == f'"polar" in classifiers'
	# unknown keywords result in an error
	with raises( RuleSyntaxError ):
		p.normalize( 'unknown_keyword' )

	# todo: more tests with the normal rule engine syntax need to go in here
	# single equal is allowed and will be expanded to double
	assert p.normalize( 'id=1000' ) == 'id == 1000'

	# normal expressions are just passed through
	assert p.normalize( 'id!=1000' ) == 'id != 1000'

	# colon expressions
	assert p.normalize( 'id:' ) == 'id == null' # missing values are treated as null
	assert p.normalize( 'id:1000' ) == 'id == 1000' # normal case: expand to equals
	assert p.normalize( 'flag:true' ) == 'flag == true' # boolean flags
	assert p.normalize( 'flag:false' ) == 'flag == false'
	assert p.normalize( 'name:afternoon' ) == '"afternoon".as_lower in name&.as_lower' # same for unquoted strings
	assert p.normalize( 'name:"afternoon run"' ) == '"afternoon run" in name ?? ""' # allow search-like string values

	# custom normalizer handling
	assert p.normalize( 'type:run' ) == 'type&.name == "run".as_lower'

	# date + time normalizing
#	assert p.normalize( 'date:2020' ) == 'starttime_local >= d"2020-01-01T00:00:00+00:00" and starttime_local <= d"2020-12-31T23:59:59.999999+00:00"'
#	assert p.normalize( 'date:2020-05' ) == 'starttime_local >= d"2020-05-01T00:00:00+00:00" and starttime_local <= d"2020-05-31T23:59:59.999999+00:00"'
#	assert p.normalize( 'date:2020-05-13' ) == 'starttime_local >= d"2020-05-13T00:00:00+00:00" and starttime_local <= d"2020-05-13T23:59:59.999999+00:00"'
	assert p.normalize( 'date:2020' ) == 'starttime_local&.year == 2020'
	assert p.normalize( 'date:2020-05' ) == 'starttime_local&.year == 2020 and starttime_local&.month == 5'
	assert p.normalize( 'date:2020-05-13' ) == 'starttime_local&.year == 2020 and starttime_local&.month == 5 and starttime_local&.day == 13'

#	assert p.normalize( 'time:10' ) == '__time__ >= d"0001-01-01T10:00:00+00:00" and __time__ <= d"0001-01-01T10:59:59.999999+00:00"'
#	assert p.normalize( 'time:10:30' ) == '__time__ >= d"0001-01-01T10:30:00+00:00" and __time__ <= d"0001-01-01T10:30:59.999999+00:00"'
#	assert p.normalize( 'time:10:30:50' ) == '__time__ >= d"0001-01-01T10:30:50+00:00" and __time__ <= d"0001-01-01T10:30:50.999999+00:00"'
	assert p.normalize( 'time:10' ) == 'starttime_local&.hour == 10'
	assert p.normalize( 'time:10:30' ) == 'starttime_local&.hour == 10 and starttime_local&.minute == 30'
	assert p.normalize( 'time:10:30:50' ) == 'starttime_local&.hour == 10 and starttime_local&.minute == 30 and starttime_local&.second == 50'

@mark.unit
def test_evaluate_engine( parser ):
	assert parser.evaluate_normalized( 'id == 1', a )

	# test null handling
	assert parser.evaluate_normalized( 'location_place == null', a )
	assert parser.evaluate_normalized( '"Berlin".as_lower in (location_city.as_lower ?? "")', a )
	assert parser.evaluate_normalized( '"Berlin".as_lower in location_city&.as_lower', a ) # safe access is possible too
	assert not parser.evaluate_normalized( '"Berlin" in (location_place ?? "")', a )

	# test lists
	assert parser.evaluate_normalized( '"Hiking" in tags', a )
	assert parser.evaluate_normalized( '[ "afternoon".as_lower == t.as_lower for t in tags ]', a )

	a.equipment = None # nullify equipment
	assert not parser.evaluate_normalized( '"shoes".as_lower in [ e.as_lower for e in equipment ?? [] ]', a )

	# test access to datetime properties
	assert parser.evaluate_normalized( 'starttime.year == 2022', a )
	assert parser.evaluate_normalized( 'starttime.year == 2022 and starttime.month == 10', a )
	assert not parser.evaluate_normalized( 'endtime.year == 2022', a ) # endtime is None
	assert not parser.evaluate_normalized( 'endtime&.year == 2022', a ) # not sure why the above line works without safe access

@mark.unit
def test_evaluate( parser ):
	assert parser.evaluate( 'id=1', a )
	assert parser.evaluate( f'year=2022', a )
	assert parser.evaluate( 'classifier:polar', a )

	b = evolve( a, name='Berlin' )

	assert parser.evaluate( 'name=Berlin', b )
	assert not parser.evaluate( 'name=berlin', b )

	assert parser.evaluate( 'name="Afternoon Hike"', a )
	assert not parser.evaluate( 'description="morning run in berlin"', a )

	assert parser.evaluate( 'name:berlin', b )
	assert not parser.evaluate( 'name:hamburg', b )
#	assert parser.evaluate( 'description:"Afternoon Hike"', a )
#	assert not parser.evaluate( 'description:"afternoon hike"', a )

	assert parser.evaluate( 'location_city:berlin', a )

@mark.unit
def test_type( parser ):
	assert parser.evaluate( 'type:walk', a )
	assert parser.evaluate( 'type:WALK', a )

@mark.unit
def test_list( parser ):
	assert parser.evaluate( '1,2,3', a )
	assert not parser.evaluate( '2,3,4', a )

@mark.unit
def test_range( parser ):
	assert not parser.evaluate( 'id=1..3', a )

	assert parser.evaluate( 'id:1..3', a )
	assert parser.evaluate( 'id:1.0..3', a ) # mixed int/float works as well
	assert parser.evaluate( 'id:1..', a )
	assert parser.evaluate( 'id:..3', a )

	assert not parser.evaluate( 'id:2..4', a )
	assert not parser.evaluate( 'id:2..', a )

	assert parser.evaluate( 'heartrate:100.0..200.0', a )

@mark.unit
def test_date_time( parser ):
	assert parser.evaluate( 'date:2022', a )
	assert parser.evaluate( 'date:2022-10', a )
	assert parser.evaluate( 'date:2022-10-16', a )

	assert not parser.evaluate( 'date:2023', a )
	assert not parser.evaluate( 'date:2023-01', a )
	assert not parser.evaluate( 'date:2023-01-13', a )

	assert parser.evaluate( 'date:2022..2023', a )
	assert parser.evaluate( 'date:2022..', a )
	assert parser.evaluate( 'date:..2023', a )
	assert parser.evaluate( 'date:2022-01-12..2022-12', a )

	# 	starttime_local=datetime( 2022, 10, 16, 14, 23, 40, tzinfo=tzlocal() ),

	assert parser.evaluate( 'time:14', a )
	assert parser.evaluate( 'time:14:23', a )
	assert parser.evaluate( 'time:14:23:40', a )

	assert parser.evaluate( 'time:14..15', a )
	assert parser.evaluate( 'time:14..', a )
	assert parser.evaluate( 'time:..15', a )
	assert parser.evaluate( 'time:14:23..14:24', a )
	assert parser.evaluate( 'time:14:23:05..14:23:50', a )

@mark.unit
def test_parse_date_range():
	assert parse_date_range_as_str( '2022..2023' ) == ('2022-01-01T00:00:00+00:00', '2023-12-31T23:59:59.999999+00:00')
	assert parse_date_range_as_str( '2022..' ) == ('2022-01-01T00:00:00+00:00', '9999-12-31T00:00:00+00:00')
	assert parse_date_range_as_str( '..2023' ) == ('0001-01-01T00:00:00+00:00', '2023-12-31T23:59:59.999999+00:00')

	assert parse_date_range_as_str( '2022-03..2022-03' ) == ('2022-03-01T00:00:00+00:00', '2022-03-31T23:59:59.999999+00:00')
	assert parse_date_range_as_str( '..2022-03' ) == ('0001-01-01T00:00:00+00:00', '2022-03-31T23:59:59.999999+00:00')
	assert parse_date_range_as_str( '2022-03..' ) == ('2022-03-01T00:00:00+00:00', '9999-12-31T00:00:00+00:00')

	assert parse_date_range_as_str( '2022-03-15..2022-03-16' ) == ('2022-03-15T00:00:00+00:00', '2022-03-16T23:59:59.999999+00:00')
	assert parse_date_range_as_str( '..2022-03-16' ) == ('0001-01-01T00:00:00+00:00', '2022-03-16T23:59:59.999999+00:00')
	assert parse_date_range_as_str( '2022-03-15..' ) == ('2022-03-15T00:00:00+00:00', '9999-12-31T00:00:00+00:00')


from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from logging import getLogger
from re import compile, match, VERBOSE
from sys import maxsize
from typing import Any, ClassVar, Dict, Iterable, Iterator, List, Literal, Tuple, Type, Union

from arrow import Arrow, get as getarrow
from attrs import define, field
from dateutil.tz import UTC
from more_itertools.recipes import first_true
from rule_engine import Context as RuleContext, resolve_attribute, Rule, RuleSyntaxError, SymbolResolutionError
from rule_engine.builtins import Builtins

from tracs.activity import Activity
from tracs.core import get_field, Keyword, Normalizer
from tracs.utils import floor_ceil_from

log = getLogger( __name__ )

TIME_FRAMES = Literal[ 'year', 'quarter', 'month', 'week', 'day', 'hour' ]

# simple items

TRUE_FALSE = compile( r'^(true|false)$' )
BOOL = compile( r'(?P<bool>true|false)' )
INT = compile( r'(?P<int>\d+)' )
NUMBER = compile( r'(?P<number>\d+(\.\d+)?)' )
QUOTED_STRING = compile( r'"(?P<string>.*)"' )
KEYWORD = compile( r'[a-zA-Z][\w_-]*' )

# lists

INT_LIST = compile( r"""
	(?P<list>
	(\d+),(\d+)
	(?:,(\d+))*
	)
""", VERBOSE )

LIST = compile( r"""
	(?P<list>
	(\w+),(\w+)
	(?:,(\w+))*
	)
""", VERBOSE )

# ranges

INT_RANGE = compile( r"""
	(\d+)?
	\.\.
	(\d+)?
""", VERBOSE )

RANGE = compile( r"""
	(?P<range_from>\d[\d.:-]*)?
	\.\.
	(?P<range_to>\d[\d.:-]*)?
""", VERBOSE )

DATE_RANGE = compile( r"""
	(?:
		(?P<year_from>[12]\d\d\d)
		(?:
			-(?P<month_from>[01]\d)
		)?
		(?:
			-(?P<day_from>[0-3]\d)
		)?
	)?
	\.\.
	(?:
		(?P<year_to>[12]\d\d\d)
		(?:
			-(?P<month_to>[01]\d)
		)?
		(?:
			-(?P<day_to>[0-3]\d)
		)?
	)?
""", VERBOSE )


TIME_RANGE = compile( r"""
	(?:
		(?P<hour_from>[0-2]\d)
		(?:
			:(?P<min_from>[0-5]\d)
		)?
		(?:
			:(?P<sec_from>[0-5]\d)
		)?
	)?
	\.\.
	(?:
		(?P<hour_to>[0-2]\d)
		(?:
			:(?P<min_to>[0-5]\d)
		)?
		(?:
			:(?P<sec_to>[0-5]\d)
		)?
	)?
""", VERBOSE )

DATE = compile( r"""
	(?P<year>[12]\d\d\d)
	-
	(?P<month>[01]\d)
	-
	(?P<day>[0-3]\d)
""", VERBOSE )

FUZZY_DATE = compile( r"""
	(?P<year>[12]\d\d\d)
	(?:-(?P<month>[01]\d))?
	(?:-(?P<day>[0-3]\d))?
""", VERBOSE )

TIME = compile( r"""
	(?P<hour>[0-1]\d|2[0-4])
	:
	(?P<minute>[0-5]\d)
	:
	(?P<second>[0-5]\d)
""", VERBOSE )

FUZZY_TIME = compile( r"""
	(?P<hour>[0-1]\d|2[0-4])
	(?:
		:(?P<minute>[0-5]\d)
	)?
	(?:
		:(?P<second>[0-5]\d)
	)?
""", VERBOSE )

RULE = compile( r"""
	(\^)?
	(\w+)
	(==|!=|=~|!~|>=|<=|>|<|=|:)
	([\w\\.,-_:]+|".*")?
""", VERBOSE )

DATE_YEAR_PATTERN = compile( r'^(?P<year>[12]\d\d\d)$' )
DATE_YEAR_MONTH_PATTERN = compile( r'^(?P<year>[12]\d\d\d)-(?P<month>[01]\d)$' )
DATE_YEAR_MONTH_DAY_PATTERN = DATE
FUZZY_DATE_PATTERN = compile( r'^(?P<year>[12]\d\d\d)(-(?P<month>[01]\d))?(-(?P<day>[0-3]\d))?$' )

TIME_RANGE_PATTERN = compile(
	r'^((?P<hour_from>[0-2]\d)(:(?P<min_from>[0-5]\d))?(:(?P<sec_from>[0-5]\d))?)?\.\.((?P<hour_to>[0-2]\d)(:(?P<min_to>[0-5]\d))?(:(?P<sec_to>[0-5]\d))?)?$'
)

SHORT_RULE_PATTERN = compile( r'^(\w+)(:|=)([\w\"\.].+)$' ) # short version: id=10 or id:10 for convenience, value must begin with alphanum or "
RULE_PATTERN = compile( r'^(\^?)(\w+)(==|!=|=~|!~|>=|<=|>|<|=|:)([\w\"\\.,-]+)?$' )

# type hints to be able to parse certain string correctly (i.e. 2022 as date, not as int)
RESOLVER_TYPES: Dict[str, Type] = {
	'date': datetime,
	'time': time,
}

def resolve_custom_attribute( thing: Any, name: str ) -> Any:
	try:
		return resolve_attribute( thing, name )
	except SymbolResolutionError:
		try:
			return getattr( thing.vf, name )
		except AttributeError:
			raise SymbolResolutionError( thing=thing, symbol_name=name )

# this should also work ...
def resolve_custom_attribute_2( thing: Any, name: str ) -> Any:
	try:
		return thing.getattr( name, quiet=False )
	except AttributeError:
		raise SymbolResolutionError( thing=thing, symbol_name=name )

# CONTEXT = Context( default_value=None, resolver=resolve_custom_attribute )
# CONTEXT = Context( resolver=resolve_custom_attribute )


class ResolvingContext( RuleContext ):

	def __init__( self, *args, **kwargs ):
		super( ResolvingContext, self ).__init__( default_value=None, resolver=ResolvingContext.resolve_attr )

		# prepare for extending builtins table
		self.builtins = Builtins.from_defaults( {
			'contains': ResolvingContext.contains,
#			'version': rule_engine_version },
		} )

	@staticmethod
	def resolve_attr( thing: Any, name: str ) -> Any:
		try:
			return getattr( thing, name )
		except (AttributeError, TypeError):
			raise SymbolResolutionError( thing=thing, symbol_name=name )

	@staticmethod
	def contains( obj_value, rule_value, type ) -> bool:
		return True if obj_value is not None and rule_value in obj_value.lower() else False

CONTEXT = ResolvingContext()

# rules parser

@define
class RuleParser:

	context: RuleContext = field( default=ResolvingContext() )
	keywords: List[Keyword] = field( factory=list )
	normalizers: List[Normalizer] = field( factory=list )

	def _keys( self ) -> List[str]:
		return [k.name for k in self.keywords]

	def _keyword( self, name: str ) -> Keyword|None:
		return first_true( self.keywords, pred=lambda k: k.name == name )

	def _normalizer_names( self ) -> List[str]:
		return [n.name for n in self.normalizers]

	def _normalizer( self, name: str ) -> Normalizer|None:
		return first_true( self.normalizers, pred=lambda n: n.name == name )

	def _rule_normalizer_type( self, name: str ) -> Any:
		return n.type if ( n := self._normalizer( name ) ) else Activity.field_type( name )

	def type_of( self, attr: str ) -> str:
		return 'None'

	def evaluate( self, rule: str, obj: Any ) -> Any:
		return self.parse_rule( rule ).evaluate( obj )

	# this is mainly for testing
	def evaluate_normalized( self, rule: str, obj: Any ) -> Any:
		return self.process( rule ).evaluate( obj )

	def filter( self, rule: str, objs: Iterable[Any] ) -> Iterator[Any]:
		return self.parse_rule( rule ).filter( objs )

	def matches( self, rule: str, obj: Any ) -> bool:
		return self.parse_rule( rule ).matches( obj )

	def parse_rules( self, *rules: str ) -> List[Rule]:
		return [self.parse_rule( r ) for r in rules]

	def parse_rule( self, rule: str ) -> Rule:

		rule: str = self.normalize( rule ) # normalize rule, used for preprocessing special cases
		rule: str = self.preprocess( rule ) # preprocess, not used at the moment
		rule: Rule = self.process( rule )
		rule: Rule = self.postprocess( rule ) # create and postprocess parsed rule

		return rule

	def normalize( self, rule: str ) -> str:

		neg, left, op, right = None, None, None, None
		normalized_rule = None

		if INT.fullmatch( rule ): # integer number only
			left, right, normalized_rule = 'id', rule, f'id == {rule}'

		elif m := INT_RANGE.fullmatch( rule ):
			left, right = 'id', rule
			range_from, range_to = m.groups()
			if range_from and not range_to:
				normalized_rule = f'id >= {range_from}'
			elif not range_from and range_to:
				normalized_rule = f'id <= {range_to}'
			else:
				normalized_rule = f'id >= {range_from} and id <= {range_to}'

		elif INT_LIST.fullmatch( rule ):
			left, right, normalized_rule = 'id', rule, f'id in [{rule}]'

		elif KEYWORD.fullmatch( rule ):  # keywords
			if rule in self._keys():
				right, normalized_rule = rule, self._keyword( rule )( rule )
			else:
				raise RuleSyntaxError( f'syntax error: unsupported keyword "{rule}"' )

		elif m := RULE.fullmatch( rule ): #

			neg, left, op, right = m.groups()

			# if a normalizer for the left side of the expression exists, let the normalizer do the work
			if n := self._normalizer( left ):
				normalized_rule = n( left, op, right )

			elif op == '=':
				if NUMBER.fullmatch( right ) or QUOTED_STRING.fullmatch( right ):
					normalized_rule = f'{left} == {right}'
				elif DATE.fullmatch( right ) and RESOLVER_TYPES.get( left ) is datetime:
					normalized_rule = f'{left} == d"{right}"'
				elif TIME.fullmatch( right ) and RESOLVER_TYPES.get( left ) is time:
					normalized_rule = f'{left} == t"{right}"'
				elif BOOL.fullmatch( right ):
					normalized_rule = f'{left} == {right}'
				else:
					normalized_rule = f'{left} == "{right}"'

			elif op == ':':
				if right is None:
					normalized_rule = f'{left} == null'

				elif NUMBER.fullmatch( right ):
					normalized_rule = f'{left} == {right}'

				elif BOOL.fullmatch( right ):
					normalized_rule = f'{left} == {right}'

				elif QUOTED_STRING.fullmatch( right):
					# normalized_rule = f'{left} != null and {right.lower()} in {left}.as_lower'
					# normalized_rule = f'{left} != null and {right} in {left}'
					normalized_rule = f'{right} in {left} ?? ""'

				elif FUZZY_DATE.fullmatch( right ) and self._rule_normalizer_type( left ) in [datetime, 'datetime', 'Optional[datetime]']:
					normalized_rule = f'{left} >= d"{parse_floor_str( right )}" and {left} <= d"{parse_ceil_str( right )}"'

				elif DATE_RANGE.fullmatch( right ) and self._rule_normalizer_type( left ) is datetime:
					range_from, range_to = parse_date_range_as_str( right )
					normalized_rule = f'{left} >= d"{range_from}" and {left} <= d"{range_to}"'

				elif TIME_RANGE.fullmatch( right ) and self._rule_normalizer_type( left ) is datetime:
					normalized_rule = '{0} >= d"{1}" and {0} <= d"{2}"'.format( left, *parse_time_range( right, as_str=True ) )

				elif m2 := RANGE.fullmatch( right ):
					range_from, range_to = parse_number_range( right )
					normalized_rule = f'{left} >= {range_from} and {left} <= {range_to}'

				else:
					# normalized_rule = f'{left} != null and "{right.lower()}" in {left}.as_lower'
					# normalized_rule = f'$contains( {left}, "{right}", "{self.type_of( left )}" )'
					field = get_field( Activity, left )
					match str( field.type ):
						case 'str':
							normalized_rule = f'"{right}".as_lower in {left}&.as_lower'
						case _:
							# raise RuleSyntaxError( f'unknown field type for "{left}"' )
							pass

			else:
				normalized_rule = f'{left} {op} {right}'

		if neg:
			normalized_rule = f'not {normalized_rule}'

		# log rule
		log.debug( f'normalized rule {rule} to {normalized_rule}' )

		# error if no rule was created
		if not normalized_rule:
			raise RuleSyntaxError( f'syntax error in expression "{rule}"' )

		return normalized_rule

	# noinspection PyMethodMayBeStatic
	def preprocess( self, rule: str ) -> str:
		"""
		Reserved for future use, does nothing at the moment.

		:param rule: rule string to preprocess
		:return: preprocessed rule
		"""
		preprocessed_rule = rule

		if rule != preprocessed_rule:
			log.debug( f'preprocessed rule {rule} to {preprocessed_rule}' )

		return preprocessed_rule

	# noinspection PyMethodMayBeStatic
	def process( self, rule: str ) -> Rule:
		"""
		Creates a rule from a normalized and preprocessed rule string.

		:param rule: rule string to use for rule creation
		:return: newly created rule
		"""
		return Rule( rule, self.context )

	# noinspection PyMethodMayBeStatic
	def postprocess( self, rule: Rule ) -> Rule:
		"""
		Reserved for future use, does nothing at the moment.

		:param rule: rule to postprocess
		:return: postprocessed rule
		"""
		postprocessed_rule = rule

		if rule != postprocessed_rule:
			log.debug( f'postprocessed rule {rule} to {postprocessed_rule}' )

		return postprocessed_rule

# helper

def parse_number_range( s: str ) -> Tuple[str, str]:
	left, right = s.split( '..', maxsplit=1 )
	try:
		range_from = Decimal( left )
	except( TypeError, InvalidOperation ):
		range_from = Decimal( ~maxsize )

	try:
		range_to = Decimal( right )
	except( TypeError, InvalidOperation ):
		range_to = Decimal( maxsize )

	return str( range_from ), str( range_to )

def parse_date_range_as_str( r: str ) -> Tuple[str, str]:
	range_from, range_to = parse_date_range( r )
	# return range_from.strftime( '%Y-%m-%d' ), range_to.strftime( '%Y-%m-%d' )
	return range_from.isoformat(), range_to.isoformat()

def parse_date_range( r: str ) -> Tuple[datetime, datetime]:
	left, right = r.split( '..', maxsplit=1 )
	return parse_floor( left ), parse_ceil( right )

def parse_time_range( r: str, as_str: bool = False ) -> Union[Tuple[datetime, datetime], Tuple[str, str]]:
	left, right = r.split( '..', maxsplit=1 )
	left = floor_ceil_from( left )[0] if left else getarrow( '00:00:00', 'HH:mm:ss' )
	right = floor_ceil_from( right )[0] if right else getarrow( '23:59:59.999999', 'HH:mm:ss.SSSSSS' )
	if as_str:
		left, right = left.isoformat(), right.isoformat()
	return left, right

def parse_floor_str( s: str ) -> str:
	return parse_floor( s ).strftime( '%Y-%m-%d' )

def parse_floor( s: str ) -> datetime:
	if match( DATE_YEAR_PATTERN, s ):
		dt = getarrow( s ).floor( 'year' )
	elif match( DATE_YEAR_MONTH_PATTERN, s ):
		dt = getarrow( s ).floor( 'month' )
	elif match( DATE_YEAR_MONTH_DAY_PATTERN, s ):
		dt = getarrow( s ).floor( 'day' )
	else:
		dt = getarrow( 1, 1, 1 )
	return dt.datetime.astimezone( UTC )

def parse_ceil_str( s: str ) -> str:
	return parse_ceil( s ).strftime( '%Y-%m-%d' )

def parse_ceil( s: str ) -> datetime:
	if match( DATE_YEAR_PATTERN, s ):
		dt = getarrow( s ).ceil( 'year' )
	elif match( DATE_YEAR_MONTH_PATTERN, s ):
		dt = getarrow( s ).ceil( 'month' )
	elif match( DATE_YEAR_MONTH_DAY_PATTERN, s ):
		dt = getarrow( s ).ceil( 'day' )
	else:
		dt = getarrow( 9999, 12, 31 )
	return dt.datetime.astimezone( UTC )

def ceil( a: Arrow, frame: TIME_FRAMES ) -> str:
	return f'd"{a.ceil( frame ).isoformat()}"'

def floor( a: Arrow, frame: TIME_FRAMES ) -> str:
	return f'd"{a.floor( frame ).isoformat()}"'

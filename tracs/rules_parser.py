
from __future__ import annotations

from datetime import datetime
from datetime import time
from logging import getLogger
from re import match
from sys import maxsize
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Type

from arrow import Arrow
from rule_engine import Context
from rule_engine import resolve_attribute
from rule_engine import Rule as DefaultRule
from rule_engine import RuleSyntaxError

from tracs.rules import Rule
from tracs.rules import NumberEqRule

log = getLogger( __name__ )

INT_PATTERN = '^(?P<value>\d+)$'
INT_LIST_PATTERN = '^(?P<values>(\d+,)+(\d+))$'
INT_RANGE_PATTERN = '^(?P<range_from>\d+)?\.\.(?P<range_to>\d+)?$'

NUMBER_PATTERN = '^(?P<value>\d+(\.\d+)?)$'

QUOTED_STRING_PATTERN = '^"(?P<value>.*)"$'

KEYWORD_PATTERN = '^[a-zA-Z][\w-]*$'

RANGE_PATTERN = '^(?P<range_from>\d[\d\.\:-]+)?(\.\.)(?P<range_to>\d[\d\.\:-]+)?$'

DATE_YEAR_PATTERN = '^(?P<year>[12]\d\d\d))$'
DATE_MONTH_PATTERN = '^(?P<year>[12]\d\d\d)-(?P<month>[01]\d)$'
DATE_PATTERN = '^(?P<year>[12]\d\d\d)-(?P<month>[01]\d)-(?P<day>[0-3]\d)$'
FUZZY_DATE_PATTERN = '^(?P<year>[12]\d\d\d)(-(?P<month>[01]\d))?(-(?P<day>[0-3]\d))?$'
TIME_PATTERN = '^(?P<hour>[0-1]\d|2[0-4]):(?P<minute>[0-5]\d):(?P<second>[0-5]\d)$'

SHORT_RULE_PATTERN = r'^(\w+)(:|=)([\w\"\.].+)$' # short version: id=10 or id:10 for convenience, value must begin with alphanum or "
RULE_PATTERN = '^(\w+)(==|!=|=~|!~|>=|<=|>|<|=|:)([\w\"\.].+)$'

RULES: Dict[str, Type[Rule]] = {
	'id': NumberEqRule
}

# mapping of keywords to normalized expressions
# this enables operations like 'list thisyear'
KEYWORDS: Dict[str, Callable] = {
	# date related keywords
	# thisweek, lastweek, today, yesterday
	'lastyear': lambda s: f'year == {datetime.utcnow().year - 1}',
	'thisyear': lambda s: f'year == {datetime.utcnow().year}',
	# todo: this needs to be detected automatically
	'bikecitizens': lambda s: f'"bikecitizens" in __classifiers__',
	'local': lambda s: f'"local" in __classifiers__',
	'polar': lambda s: f'"polar" in __classifiers__',
	'strava': lambda s: f'"strava" in __classifiers__',
	'waze': lambda s: f'"waze" in __classifiers__',
}

# normalizers transform a field/value pair into a valid normalized expression
# this enables operations like 'list classifier:polar' where ':' does not evaluate to '=='
NORMALIZERS: Dict[str, Callable] = {
	'classifier': lambda s: f'"{s}" in __classifiers__',
}

# custom resolvers, needed to access "virtual fields" which do not exist
# the key represents the name of the virtual field, the value is a function which calculates the actual value
RESOLVERS: Dict[str, Callable] = {
	# date/time fields
	'weekday': lambda t, n: t.time.day, # day attribute of datetime objects
	'day': lambda t, n: t.time.day, # day attribute of datetime objects
	'month': lambda t, n: t.time.month, # month attribute of datetime objects
	'year': lambda t, n: t.time.year, # year attribute of datetime objects
	'date': lambda t, n: t.time.date(), # date
	# activity type
	'type': lambda t, n: t.type.value,
	# internal helper attributes, which are not intended to be used directly
	'__classifiers__': lambda t, n: list( map( lambda s: s.split( ':', 1 )[0], t.uids ) ), # virtual attribute of uids
	'__date__': lambda t, n: t.time.date(), # date
	'__time__': lambda t, n: t.time.time(), # time
}

# type hints to be able to parse certain string correctly (i.e. 2022 as date, not as int)
RESOLVER_TYPES: Dict[str, Type] = {
	'date': datetime,
	'time': time,
}

def resolve_custom_attribute( thing: Any, name: str ):
	return RESOLVERS[name]( thing, name ) if name in RESOLVERS.keys() else resolve_attribute( thing, name )

# CONTEXT = Context( default_value=None, resolver=resolve_custom_attribute )
CONTEXT = Context( resolver=resolve_custom_attribute )

# predefined rules

# rules parser

def parse_rules( *rules: str ) -> List[DefaultRule]:
	return [parse_rule( r ) for r in rules]

def parse_rule( rule: str ) -> DefaultRule:

	rule: str = normalize( rule ) # normalize rule, used for preprocessing special cases
	rule: str = preprocess( rule ) # preprocess, not used at the moment
	rule: DefaultRule = process( rule )
	rule: Rule = postprocess( rule ) # create and postprocess parsed rule

	return rule

def normalize( rule: str ) -> str:

	normalized_rule = rule

	if m := match( INT_PATTERN, rule ): # integer number only
		normalized_rule = f'id == {rule}'

	elif m := match( KEYWORD_PATTERN, rule ):  # keywords
		if rule in KEYWORDS:
			normalized_rule = KEYWORDS[rule]( rule )
		else:
			raise RuleSyntaxError( f'syntax error: unsupported keyword "{rule}"' )

	elif m := match( RULE_PATTERN, rule ): #
		left, op, right = m.groups()

		if op == '=':
			if match( NUMBER_PATTERN, right ) or match( QUOTED_STRING_PATTERN, right ):
				normalized_rule = f'{left} == {right}'
			elif RESOLVER_TYPES.get( left ) is datetime and match( DATE_PATTERN, right ):
				normalized_rule = f'{left} == d"{right}"'
			elif RESOLVER_TYPES.get( left ) is time and match( TIME_PATTERN, right ):
				normalized_rule = f'{left} == t"{right}"'
			else:
				normalized_rule = f'{left} == "{right}"'

		elif op == ':':
			if left in NORMALIZERS:
				normalized_rule = NORMALIZERS[left]( right )
			elif match( NUMBER_PATTERN, right ):
				# datetime years are caught by this regex already ...
				if RESOLVER_TYPES.get( left ) is datetime:
					normalized_rule = f'{left} >= d"{right}-01-01" and {left} <= d"{right}-12-31"'
				else:
					normalized_rule = f'{left} == {right}'

			elif match (QUOTED_STRING_PATTERN, right):
				normalized_rule = f'{left} != null and {right.lower()} in {left}.as_lower'

			elif RESOLVER_TYPES.get( left ) is datetime:
				if dm := match( DATE_MONTH_PATTERN, right ):
					year, month = dm.groups()
					floor = f'{year}-{month}-01'
					ceil = Arrow( int( year ), int( month ), 15 ).ceil( 'month' ).format( 'YYYY-MM-DD' )
					normalized_rule = f'{left} >= d"{floor}" and {left} <= d"{ceil}"'
				elif dm := match( DATE_PATTERN, right ):
					year, month, day = dm.groups()
					floor = f'{year}-{month}-{day}'
					ceil = Arrow( int( year ), int( month ), int( day ) ).ceil( 'day' ).format( 'YYYY-MM-DD' )
					normalized_rule = f'{left} >= d"{floor}" and {left} <= d"{ceil}"'

			elif rm := match( RANGE_PATTERN, right ):
				left_range, range_op, right_range = rm.groups()

				right_range = maxsize if right_range is None and match( NUMBER_PATTERN, left_range ) else right_range
				left_range = 0 if left_range is None and match( NUMBER_PATTERN, right_range ) else left_range

				normalized_rule = f'{left} >= {left_range} and {left} <= {right_range}'
			else:
				normalized_rule = f'{left} != null and "{right.lower()}" in {left}.as_lower'

		else:
			normalized_rule = f'{left} {op} {right}'

	else:
		raise RuleSyntaxError( f'syntax error in expression "{rule}"' )

	log.debug( f'normalized rule {rule} to {normalized_rule}' )

	return normalized_rule

def preprocess( rule: str ) -> str:
	"""
	Reserved for future use, does nothing at the moment.

	:param rule: rule string to preprocess
	:return: preprocessed rule
	"""
	preprocessed_rule = rule

	if rule != preprocessed_rule:
		log.debug( f'preprocessed rule {rule} to {preprocessed_rule}' )

	return preprocessed_rule

def process( rule: str ) -> Rule:
	return DefaultRule( rule, CONTEXT )

	if m := match( RULE_PATTERN, rule ):
		return process_expr( rule, *m.groups() )
	else:
		raise RuntimeError( f'unable to parse rule {rule}' )

def process_expr( rule: str, left: str, op: str, right: str ) -> DefaultRule:
	pass
#	if left not in RULES.keys():
#		raise RuntimeError( f'unknown/unsupported query field {left}' )

#	if op not in RULES.get( left ).compatible_ops:
#		raise RuntimeError( f'unknown/unsupported operator "{op}" for query field {left}' )


	# rule = create_rule( left, op, right )
	# return rule

def create_rule( left: str, op: str, right: str ) -> Rule:
	return RULES.get( left )( field=left, operator=op, value=right )

def postprocess( rule: DefaultRule ) -> DefaultRule:

	postprocessed_rule = rule

	if rule != postprocessed_rule:
		log.debug( f'postprocessed rule {rule} to {postprocessed_rule}' )

	return postprocessed_rule

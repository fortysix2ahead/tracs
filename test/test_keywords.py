
from __future__ import annotations

from tracs.core import Keyword
from tracs.registry import Registry

def test_keywords():
	import tracs.plugins.rule_extensions
	assert kw( 'morning' )() == 'hour >= 6 and hour < 11'
	assert kw( 'thisyear' )().startswith( 'time >= d"20' )

def kw( name: str ) -> Keyword:
	return Registry.rule_keywords.get( name )

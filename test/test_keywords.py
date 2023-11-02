
from __future__ import annotations

from logging import getLogger

from tracs.core import Keyword
from tracs.registry import Registry

log = getLogger( __name__ )

def setup_module( module ):
	# noinspection PyUnresolvedReferences
	import tracs.plugins.rule_extensions
	log.info( 'importing tracs.plugins.rule_extensions' )

def test_keywords():

	assert kw( 'morning' )() == 'hour >= 6 and hour < 11'
	assert kw( 'thisyear' )().startswith( 'starttime_local >= d"20' )

def kw( name: str ) -> Keyword:
	return Registry.instance().keywords.get( name )

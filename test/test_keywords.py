
from __future__ import annotations

from logging import getLogger

from tracs.pluginmgr import PluginManager
from tracs.core import Keyword

log = getLogger( __name__ )

def setup_module( module ):
	# noinspection PyUnresolvedReferences
	import tracs.plugins.keywords
	log.info( 'importing tracs.plugins.keywords' )

def test_keywords():
	assert kw( 'morning' )() == 'hour >= 6 and hour < 11'
	assert kw( 'thisyear' )().startswith( 'starttime_local >= d"20' )

def kw( name: str ) -> Keyword:
	return PluginManager.inst().registry()._keyword.get( name )


from __future__ import annotations

from tracs.plugins.keywords import KEYWORDS
from tracs.core import Keyword

def test_keywords():
	assert kw( 'morning' )() == 'hour >= 6 and hour < 11'
	assert kw( 'thisyear' )().startswith( 'time >= d"20' )

def kw( name: str ) -> Keyword:
	return next( k for k in KEYWORDS if k.name == name )

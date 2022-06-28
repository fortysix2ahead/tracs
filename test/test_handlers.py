from datetime import datetime

from tracs.plugins.handlers import GPXHandler
from tracs.plugins.handlers import JSONHandler
from .helpers import get_file_path

def test_json_handler():
	p = get_file_path( 'templates/polar/2020.json' )
	content = JSONHandler().load( p )
	assert content is not None and len( content ) > 0

def test_gpx_handler():
	p = get_file_path( 'templates/gpx/mapbox.gpx' )
	content = GPXHandler().load( p )
	assert content.time is not None and type( content.time ) is datetime

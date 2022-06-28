
from tracs.plugins.handlers import JSONHandler
from .helpers import get_file_path

def test_json_handler():
	p = get_file_path( 'templates/polar/2020.json' )
	content = JSONHandler().load( p )
	assert content is not None and len( content ) > 0

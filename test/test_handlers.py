
from datetime import datetime

from gpxpy.gpx import GPX

from tracs.plugins.handlers import GPXHandler
from tracs.plugins.handlers import JSONHandler
from .helpers import get_file_path

def test_json_handler():
	path = get_file_path( 'templates/polar/2020.json' )
	handler = JSONHandler() # todo: why does that fail, when @handler without parameters is used?
	#handler = Registry.handler_for( 'json' )

	assert handler.types() == ['json']

	json = handler.load( path )
	assert json is not None and len( json ) > 0

def test_gpx_handler():
	path = get_file_path( 'templates/gpx/mapbox.gpx' )
	handler = GPXHandler()

	assert handler.types() == ['gpx']

	data = handler.load( path )
	assert type( data ) is GPX
	assert data.time is not None and type( data.time ) is datetime

	activity = handler.import_from( data )
	assert activity.raw_id is not None and activity.time is not None
	assert activity.resources == []

	activity = handler.import_from( data, path )
	assert activity.raw_id is not None and activity.time is not None
	assert activity.resources[0].path is not None
	assert activity.resources[0].raw_data is not None

	activity = handler.import_from( path=path )
	assert activity.raw_id is not None and activity.time is not None
	assert activity.resources[0].path is not None
	assert activity.resources[0].raw_data is not None

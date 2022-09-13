
from datetime import datetime

from tracs.plugins import Registry
from tracs.plugins.bikecitizens import BIKECITIZENS_TYPE
from tracs.plugins.bikecitizens import BikecitizensActivity
from tracs.plugins.handlers import GPXActivity
from tracs.plugins.handlers import XML_TYPE
from tracs.plugins.polar import PolarActivity
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.strava import StravaActivity
from tracs.plugins.waze import WAZE_TYPE
from tracs.plugins.waze import WazeActivity
from .helpers import get_file_path

def test_json_importer():
	path = get_file_path( 'templates/polar/2020.json' )
	importer = Registry.importer_for( 'application/json' )
	assert importer.types == ['application/json']

	json = importer.load( path=path )
	assert json is not None and len( json ) > 0

def test_xml_importer():
	path = get_file_path( 'templates/polar/empty.gpx' )
	importer = Registry.importer_for( XML_TYPE )
	assert importer.types == [XML_TYPE]

	xml = importer.load( path=path )
	assert xml is not None and xml.getroot() is not None

def test_gpx_importer():
	path = get_file_path( 'templates/gpx/mapbox.gpx' )
	importer = Registry.importer_for( 'application/xml+gpx' )

	assert importer.types == ['application/xml+gpx']

	activity = importer.load( path=path )
	assert type( activity ) is GPXActivity
	assert activity.time is not None and type( activity.time ) is datetime
	assert activity.raw_id is not None
	assert activity.resources[0].path is not None
	assert activity.resources[0].raw_data is not None

def test_polar_importer():
	path = get_file_path( 'libraries/default/polar/1/0/0/100001/100001.raw.json' )
	importer = Registry.importer_for( 'application/json+polar' )

	assert importer.types == ['application/json+polar']

	activity = importer.load( path=path )
	assert type( activity ) is PolarActivity and activity.uid == 'polar:100001'

def test_strava_importer():
	path = get_file_path( 'libraries/default/strava/2/0/0/200002/200002.raw.json' )
	importer = Registry.importer_for( STRAVA_TYPE )

	assert importer.types == [STRAVA_TYPE]

	activity = importer.load( path=path )
	assert type( activity ) is StravaActivity and activity.uid == 'strava:200002'

def test_bikecitizens_importer():
	path = get_file_path( 'libraries/default/bikecitizens/1/0/0/1000001/1000001.raw.json' )
	importer = Registry.importer_for( BIKECITIZENS_TYPE )

	assert importer.types == [BIKECITIZENS_TYPE]

	activity = importer.load( path=path )
	assert type( activity ) is BikecitizensActivity and activity.uid == 'bikecitizens:1000001'

def test_waze_importer():
	path = get_file_path( 'libraries/default/waze/20/07/12/200712074743/200712074743.raw.txt' )
	importer = Registry.importer_for( WAZE_TYPE )

	assert importer.types == [WAZE_TYPE]

	activity = importer.load( path=path )
	assert type( activity ) is WazeActivity and activity.uid == 'waze:200712074743'

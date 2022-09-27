
from datetime import datetime

from tracs.plugins import Registry
from tracs.plugins.bikecitizens import BIKECITIZENS_TYPE
from tracs.plugins.bikecitizens import BikecitizensActivity
from tracs.plugins.handlers import GPXActivity
from tracs.plugins.handlers import JSON_TYPE
from tracs.plugins.handlers import XML_TYPE
from tracs.plugins.polar import POLAR_EXERCISE_DATA_TYPE
from tracs.plugins.polar import POLAR_FLOW_TYPE
from tracs.plugins.polar import PolarActivity
from tracs.plugins.polar import PolarExerciseDataActivity
from tracs.plugins.strava import STRAVA_TYPE
from tracs.plugins.strava import StravaActivity
from tracs.plugins.waze import WAZE_TYPE
from tracs.plugins.waze import WazeActivity
from .helpers import get_file_path

def test_json_importer():
	path = get_file_path( 'templates/polar/2020.json' )
	importer = Registry.importer_for( 'application/json' )

	rsrc = importer.load( path=path )
	assert rsrc.type == JSON_TYPE
	assert type( rsrc.content ) is bytes and len( rsrc.content ) > 0
	assert type( rsrc.text ) is str and len( rsrc.text ) > 0
	assert type( rsrc.raw_data ) is list

def test_xml_importer():
	path = get_file_path( 'templates/polar/empty.gpx' )
	importer = Registry.importer_for( XML_TYPE )

	rsrc = importer.load( path=path )
	assert rsrc.type == XML_TYPE
	assert type( rsrc.content ) is bytes and len( rsrc.content ) > 0
	assert type( rsrc.text ) is str and len( rsrc.text ) > 0
	assert rsrc.raw_data.getroot() is not None

def test_gpx_importer():
	path = get_file_path( 'templates/gpx/mapbox.gpx' )
	importer = Registry.importer_for( 'application/xml+gpx' )

	activity = importer.load( path=path )
	assert type( activity ) is GPXActivity
	assert activity.time is not None and type( activity.time ) is datetime
	assert activity.raw_id is not None
	assert activity.resources[0].path is not None
	assert activity.resources[0].raw_data is not None

def test_polar_importer():
	path = get_file_path( 'libraries/default/polar/1/0/0/100001/100001.raw.json' )
	importer = Registry.importer_for( POLAR_FLOW_TYPE )
	assert importer.type == POLAR_FLOW_TYPE
	assert importer.activity_cls == PolarActivity

	activity = importer.load( path=path )
	assert type( activity ) is PolarActivity and activity.uid == 'polar:100001'

def test_polar_ped_importer():
	path = get_file_path( 'templates/polar/personal_trainer/20160904.xml' )
	importer = Registry.importer_for( POLAR_EXERCISE_DATA_TYPE )
	assert importer.type == POLAR_EXERCISE_DATA_TYPE
	assert importer.activity_cls == PolarExerciseDataActivity

	activity = importer.load( path=path )
	assert type( activity ) is PolarExerciseDataActivity and activity.uid == 'polar:160904124614'

def test_strava_importer():
	path = get_file_path( 'libraries/default/strava/2/0/0/200002/200002.raw.json' )
	importer = Registry.importer_for( STRAVA_TYPE )
	assert importer.type == STRAVA_TYPE
	assert importer.activity_cls == StravaActivity

	activity = importer.load( path=path )
	assert type( activity ) is StravaActivity and activity.uid == 'strava:200002'

def test_bikecitizens_importer():
	path = get_file_path( 'libraries/default/bikecitizens/1/0/0/1000001/1000001.raw.json' )
	importer = Registry.importer_for( BIKECITIZENS_TYPE )
	assert importer.type == BIKECITIZENS_TYPE
	assert importer.activity_cls == BikecitizensActivity

	activity = importer.load( path=path )
	assert type( activity ) is BikecitizensActivity and activity.uid == 'bikecitizens:1000001'

def test_waze_importer():
	path = get_file_path( 'libraries/default/waze/20/07/12/200712074743/200712074743.raw.txt' )
	importer = Registry.importer_for( WAZE_TYPE )
	assert importer.type == WAZE_TYPE
	assert importer.activity_cls == WazeActivity

	activity = importer.load( path=path )
	assert type( activity ) is WazeActivity and activity.uid == 'waze:200712074743'

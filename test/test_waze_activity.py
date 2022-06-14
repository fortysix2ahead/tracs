
from datetime import datetime
from datetime import timezone
from dateutil.tz import gettz

from pytest import mark
from pytest import raises

from tracs.activity_types import ActivityTypes
from tracs.config import KEY_CLASSIFER
from tracs.plugins.waze import read_drive
from tracs.plugins.waze import read_takeout
from tracs.plugins.waze import Waze
from tracs.plugins.waze import WazeActivity

from .fixtures import db_default_inmemory
from .helpers import get_file_path

def test_read_drive():
	json = get_file_path( 'templates/waze/200712_074743.json' )
	s = json.read_bytes().decode('UTF-8')
	points = read_drive( s )
	assert len( points ) == 137

	json = get_file_path( 'templates/waze/200712_102429.json' )
	points = read_drive( json.read_bytes().decode('UTF-8') )
	assert len( points ) == 166

def test_read_takeout():
	csv = get_file_path( 'templates/waze/account_activity_3.csv' )
	takeouts = read_takeout( csv )
	assert len( takeouts ) == 2

def test_activity_from_raw():
	json = get_file_path( 'templates/waze/200712_074743.json' )
	points = read_drive( json.read_bytes().decode('UTF-8') )
	a = WazeActivity( raw=points )

	assert a['id'] == 0
	assert a['raw_id'] == 20200712074743
	assert a['time'] == datetime( 2020, 7, 12, 7, 47, 43, tzinfo=timezone.utc )
	assert a['localtime'] == datetime( 2020, 7, 12, 9, 47, 43, tzinfo=gettz() )
	assert a['type'] == ActivityTypes.drive

@mark.db_template( 'default' )
def test_activity_from_db( db, json ):
	a = WazeActivity( json['activities']['30'], 30 )

	# test id
	assert a['id'] == 30
	assert a.get('id') == 30
	assert a.id == 30
	assert a['raw_id'] == 20200101010101
	assert a.get('raw_id') == 20200101010101
	assert a.raw_id == 20200101010101

	assert a['uid'] == 'waze:20200101010101'

	assert a[KEY_CLASSIFER] == 'waze'
	assert a.get( KEY_CLASSIFER ) == 'waze'
	assert a.classifier == 'waze'
	assert a.service == 'waze'

	# name, type etc.
	assert a['name'] == 'Ungrouped Waze Drive'
	assert a.name == 'Ungrouped Waze Drive'
	assert a['type'] == ActivityTypes.drive
	assert a.get( 'type' ) == ActivityTypes.drive

	assert a['time'] == datetime( 2020, 1, 11, 12, 0, 0, tzinfo=timezone.utc )
	assert a.time == datetime( 2020, 1, 11, 12, 0, 0, tzinfo=timezone.utc )
	assert a['localtime'] == datetime( 2020, 1, 11, 13, 0, 0, tzinfo=gettz() )
	assert a.localtime == datetime( 2020, 1, 11, 13, 0, 0, tzinfo=gettz() )

	# raw data
	with raises( KeyError ):
		assert a.raw['title'] == 'whatever'

	# metadata
	assert a.metadata.get( 'path' ) is not None

	# check resources
	assert len( a.resources ) == 1

	with raises( KeyError ):
		assert a.metadata['invalid_property'] is None

def _test_fetch_download():
	activities = Waze()._fetch( 2020, get_file_path( 'templates/waze' ) )
	assert len( activities ) == 2

	for a in activities:
		Waze()._download_file( a, get_file_path( 'templates/waze' ) )

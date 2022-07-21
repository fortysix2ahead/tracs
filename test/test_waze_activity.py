
from datetime import datetime
from datetime import timezone
from dateutil.tz import gettz

from pytest import mark

from tracs.activity_types import ActivityTypes
from tracs.plugins.waze import read_drive
from tracs.plugins.waze import read_takeout
from tracs.plugins.waze import Waze
from tracs.plugins.waze import WazeActivity

from .helpers import get_file_path

def test_read_drive():
	path = get_file_path( 'templates/waze/200712_074743.json' )
	points = read_drive( path.read_bytes().decode('UTF-8') )
	assert len( points ) == 137

	path = get_file_path( 'templates/waze/200712_102429.json' )
	points = read_drive( path.read_bytes().decode('UTF-8') )
	assert len( points ) == 166

@mark.file( 'templates/waze/account_activity_3.csv' )
def test_read_takeout( path ):
	takeouts = read_takeout( path )
	assert len( takeouts ) == 2

@mark.file( 'libraries/default/waze/20/07/12/200712074743/200712074743.raw.txt' )
def test_activity_from_raw( path ):
	points = read_drive( path.read_bytes().decode('UTF-8') )
	a = WazeActivity( raw=points )

	assert a.id == 0
	assert a.raw_id == 20200712074743
	assert a.classifier == 'waze'
	assert a.uid == 'waze:20200712074743'

	assert a.time == datetime( 2020, 7, 12, 7, 47, 43, tzinfo=timezone.utc )
	assert a.localtime == datetime( 2020, 7, 12, 9, 47, 43, tzinfo=gettz() )
	assert a.type == ActivityTypes.drive

def _test_fetch_download():
	activities = Waze()._fetch( 2020, get_file_path( 'templates/waze' ) )
	assert len( activities ) == 2

	for a in activities:
		Waze()._download_resource( a, get_file_path( 'templates/waze' ) )

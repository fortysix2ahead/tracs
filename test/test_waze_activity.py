
from datetime import datetime
from datetime import timezone
from typing import cast

from dateutil.tz import gettz

from pytest import mark

from tracs.activity_types import ActivityTypes
from tracs.registry import Registry
from tracs.plugins.waze import WAZE_TAKEOUT_TYPE
from tracs.plugins.waze import WAZE_TYPE
from tracs.plugins.waze import Waze
from tracs.plugins.waze import WazeActivity
from tracs.plugins.waze import WazeImporter

from .helpers import get_file_path

@mark.file( 'templates/waze/200712_074743.json' )
def test_read_drive( path ):
	resource = Registry.importer_for( WAZE_TYPE ).load( path=path )
	assert len( resource.raw ) == 137

	s = path.read_text( 'UTF-8' )
	resource = Registry.importer_for( WAZE_TYPE ).load( from_string=s )
	assert len( resource.raw ) == 137

@mark.file( 'templates/waze/account_activity_3.csv' )
def test_read_takeout( path ):
	resource = Registry.importer_for( WAZE_TAKEOUT_TYPE ).load( path=path )
	assert len( resource.resources ) == 2
	assert all( lambda r: r.type == WAZE_TAKEOUT_TYPE for r in resource.resources )

@mark.file( 'libraries/default/waze/20/07/12/200712074743/200712074743.raw.txt' )
def test_activity_from_raw( path ):
	importer = cast( WazeImporter, Registry.importer_for( WAZE_TYPE ) )
	points = importer.read_drive( path.read_bytes().decode('UTF-8') )
	a = WazeActivity( raw=points )

	assert a.id == 0
	assert a.raw_id == 200712074743
	assert a.classifier == 'waze'
	assert a.uid == 'waze:200712074743'

	assert a.time == datetime( 2020, 7, 12, 7, 47, 43, tzinfo=timezone.utc )
	assert a.localtime == datetime( 2020, 7, 12, 9, 47, 43, tzinfo=gettz() )
	assert a.type == ActivityTypes.drive

@mark.context( library='default', config='default', cleanup=True )
@mark.service( cls=Waze )
def test_fetch( service ):
	resources = service.fetch( force=False, pretend=False )
	assert len( resources ) == 2

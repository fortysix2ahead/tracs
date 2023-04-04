
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

@mark.file( 'takeouts/waze/waze/2020-07/account_activity_3.csv' )
def test_read_takeout( path ):
	resource = Registry.importer_for( WAZE_TAKEOUT_TYPE ).load( path=path )
	assert len( resource.resources ) == 2
	assert all( lambda r: r.type == WAZE_TAKEOUT_TYPE for r in resource.resources )

@mark.file( 'libraries/default/waze/20/07/12/200712074743/200712074743.raw.txt' )
def test_activity_from_raw( path ):
	importer = cast( WazeImporter, Registry.importer_for( WAZE_TYPE ) )
	points = importer.read_drive( path.read_bytes().decode('UTF-8') )
	assert len( points ) == 137

@mark.context( library='default', config='default', takeout='waze', cleanup=False )
@mark.service( cls=Waze )
def test_fetch( service ):
	resources = service.fetch( force=False, pretend=False )
	assert len( resources ) == 2

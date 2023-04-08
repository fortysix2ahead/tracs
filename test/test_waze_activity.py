from typing import cast

from pytest import mark

from tracs.plugins.waze import AccountActivity
from tracs.plugins.waze import Waze
from tracs.plugins.waze import WAZE_ACCOUNT_ACTIVITY_TYPE
from tracs.plugins.waze import WAZE_ACCOUNT_INFO_TYPE
from tracs.plugins.waze import WAZE_TYPE
from tracs.plugins.waze import WazeImporter
from tracs.registry import Registry

@mark.file( 'takeouts/waze/waze/2020-09/account_activity_3.csv' )
def test_read_account_activity_2020( path ):
	resource = Registry.importer_for( WAZE_ACCOUNT_ACTIVITY_TYPE ).load( path=path )
	location_details = cast( AccountActivity, resource.raw ).location_details
	assert len( location_details ) == 1
	assert len( location_details[0].as_point_list() ) == 25

@mark.file( 'takeouts/waze/waze/2022-01/account_activity_3.csv' )
def test_read_account_activity_2022( path ):
	resource = Registry.importer_for( WAZE_ACCOUNT_ACTIVITY_TYPE ).load( path=path )
	location_details = cast( AccountActivity, resource.raw ).location_details
	assert len( location_details ) == 2
	assert len( location_details[0].as_point_list() ) == 310
	assert len( location_details[1].as_point_list() ) == 316

@mark.file( 'takeouts/waze/waze/2023-04/account_activity_3.csv' )
def test_read_account_activity_2023( path ):
	resource = Registry.importer_for( WAZE_ACCOUNT_ACTIVITY_TYPE ).load( path=path )
	location_details = cast( AccountActivity, resource.raw ).location_details
	assert len( location_details ) == 2
	assert len( location_details[0].as_point_list() ) == 146
	assert len( location_details[1].as_point_list() ) == 71

# dummy test case: can read, but data is not used anywhere
@mark.file( 'takeouts/waze/waze/2023-04/account_info.csv' )
def test_read_account_info( path ):
	resource = Registry.importer_for( WAZE_ACCOUNT_INFO_TYPE ).load( path=path )

@mark.file( 'libraries/default/waze/20/07/12/200712074743/200712074743.txt' )
def test_activity_from_raw( path ):
	importer = cast( WazeImporter, Registry.importer_for( WAZE_TYPE ) )
	resource = importer.load( path )
	assert len( resource.raw ) == 137

@mark.context( library='default', config='default', takeout='waze', cleanup=False )
@mark.service( cls=Waze )
def test_fetch_default( service ):
	resources = service.fetch( force=False, pretend=False )
	assert len( resources ) == 0

@mark.context( library='default', config='default', takeout='waze', cleanup=False )
@mark.service( cls=Waze )
def test_fetch_from_takeouts( service ):
	resources = service.fetch( force=False, pretend=False, from_takeouts=True )
	assert len( resources ) == 4

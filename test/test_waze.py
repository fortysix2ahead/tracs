from pathlib import Path
from typing import cast

from pytest import mark

from tracs.plugins.waze import AccountActivity, Waze, WazeAccountActivityImporter, WazeImporter

account_importer = WazeAccountActivityImporter()

@mark.unit
@mark.file( 'environments/takeouts/takeouts/waze/2020-09/account_activity_3.csv' )
def test_read_account_activity_2020( fspath ):
	resource = account_importer.load( fs=fspath.fs, path=fspath.path )
	location_details = cast( AccountActivity, resource.data ).location_details
	assert len( location_details ) == 1
	assert len( location_details[0].as_point_list() ) == 25

@mark.unit
@mark.file( 'environments/takeouts/takeouts/waze/2022-01/account_activity_3.csv' )
def test_read_account_activity_2022( fspath ):
	resource = account_importer.load( fs=fspath.fs, path=fspath.path )
	location_details = cast( AccountActivity, resource.data ).location_details
	assert len( location_details ) == 2
	assert len( location_details[0].as_point_list() ) == 310
	assert len( location_details[1].as_point_list() ) == 316

@mark.unit
@mark.file( 'environments/takeouts/takeouts/waze/2023-04/account_activity_3.csv' )
def test_read_account_activity_2023( fspath ):
	resource = account_importer.load( fs=fspath.fs, path=fspath.path )
	location_details = cast( AccountActivity, resource.data ).location_details
	assert len( location_details ) == 2
	assert len( location_details[0].as_point_list() ) == 146
	assert len( location_details[1].as_point_list() ) == 71

# dummy test case: can read, but data is not used anywhere
@mark.unit
@mark.file( 'environments/takeouts/takeouts/waze/2023-04/account_activity_3.csv' )
def test_read_account_info( path ):
	resource = account_importer.load( path=path )

@mark.unit
@mark.file( 'environments/default/db/waze/20/07/12/200712074743/200712074743.txt' )
def test_activity_from_raw( path ):
	resource = WazeImporter().load( path )
	assert len( resource.data.points ) == 137

@mark.context( env='empty', cleanup=True )
@mark.service( cls=Waze )
def test_path_for( service ):
	assert service.path_for_id( '231201102030' ) == '23/12/01/231201102030'
	assert service.path_for_id( '1' ) == '00/00/01/000001'
	assert service.path_for_id( '231201102030', 'waze' ) == 'waze/23/12/01/231201102030'
	assert service.path_for_id( '231201102030', resource_path='recording.gpx' ) == '23/12/01/231201102030/recording.gpx'
	assert service.path_for_id( '231201102030', base_path='waze', resource_path='recording.gpx' ) == 'waze/23/12/01/231201102030/recording.gpx'

	assert service.svc_path_for_id( '231201102030', 'recording.gpx' ) == 'waze/23/12/01/231201102030/recording.gpx'

@mark.context( env='takeouts', cleanup=True )
@mark.service( cls=Waze, init=True, register=True )
def test_import( service ):
	src_fs = service.ctx.takeout_fs( 'waze' )
	activities = service.import_activities( src_fs=src_fs, src_path=None, force=True )
	assert [ a.uid for a in activities ] == [
		'waze:200712102429', 'waze:211222051711', 'waze:220102191316', 'waze:230310152717'
	]

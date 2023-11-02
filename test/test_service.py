
from pathlib import Path
from typing import cast

from pytest import mark

from test.mock_service import Mock
from test.mock_service import MOCK_TYPE
from test.mock_service import MockActivity
from tracs.db import ActivityDb
from tracs.registry import Registry
from tracs.resources import Resource
from tracs.resources import ResourceType
from tracs.service import Service

@mark.service( cls=Mock )
def test_path_for( service ):
	# path for a given id
	assert service.path_for_id( '1001' ) == Path( '1/0/0/1001' )
	assert service.path_for_id( '1' ) == Path( '0/0/1/1' )
	assert service.path_for_id( '1001', Path( 'test' ) ) == Path( 'test/1/0/0/1001' )
	assert service.path_for_id( '1001', resource_path=Path( 'recording.gpx' ) ) == Path( '1/0/0/1001/recording.gpx' )
	assert service.path_for_id( '1001', Path( 'test' ), Path( 'recording.gpx' ) ) == Path( 'test/1/0/0/1001/recording.gpx' )

	# path for a uid (this calls path_for_id internally)
	assert Service.path_for_uid( 'mock:1001' ) == Path( 'mock/1/0/0/1001' )
	assert Service.path_for_uid( 'mock:0' ) == Path( 'mock/0/0/0/0' )
	# assert Service.path_for_uid( 'unknown:1001' ) is None
	assert Service.path_for_uid( 'unknown:1001' ) == Path( 'unknown/1/0/0/1001' ) # uids for unregistered services are supported as well

	# paths for resources
	r = Resource( uid='mock:1001', path='recording.gpx' )
	assert service.path_for( r, absolute=False ) == Path( 'mock/1/0/0/1001/recording.gpx' )
	assert service.path_for( r, absolute=True ) == Path( Path( service.ctx.db_dir_path ), 'mock/1/0/0/1001/recording.gpx' )
	assert service.path_for( r, absolute=False, omit_classifier=True ) == Path( '1/0/0/1001/recording.gpx' )
	assert service.path_for( r, absolute=True, omit_classifier=True ) == Path( Path( service.ctx.db_dir_path ), 'mock/1/0/0/1001/recording.gpx' )

@mark.context( config='empty', library='empty', cleanup=False )
@mark.service( cls=Mock )
def test_fetch( service ):
	db = cast( ActivityDb, service.ctx.db )
	service.import_activities( skip_download=True, skip_link=True )
	assert len( db.activities ) == 3

	p = Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.json' )
	assert p.exists() and not Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.gpx' ).exists()

	# test force flag
	mtime = p.stat().st_mtime
	service.import_activities( skip_download=True, skip_link=True )
	assert p.stat().st_mtime == mtime
	service.import_activities( force=True, skip_download=True, skip_link=True )
	assert p.stat().st_mtime > mtime

	# test pretend flag
	mtime = p.stat().st_mtime
	service.import_activities( force=True, pretend=True, skip_download=True, skip_link=True )
	assert p.stat().st_mtime == mtime

@mark.context( config='empty', library='empty', cleanup=False )
@mark.service( cls=Mock )
def test_download( service ):
	Registry.instance().resource_types[MOCK_TYPE] = ResourceType( type=MOCK_TYPE, activity_cls=MockActivity ) # register mock type manually

	service.import_activities( skip_download=False, skip_link=True )

	assert len( service.ctx.db.resources ) == 6
	assert len( service.ctx.db.activities ) == 3

	p = Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.gpx' )
	assert p.exists()

@mark.service( cls=Mock )
def test_filter_fetched( service ):
	resources = [
		Resource( uid='polar:10' ),
		Resource( uid='polar:20' ),
		Resource( uid='polar:30' ),
	]

	assert service.filter_fetched( resources, 'polar:20' ) == [resources[1]]
	assert service.filter_fetched( resources, 'polar:10', 'polar:20' ) == [resources[0], resources[1]]
	assert service.filter_fetched( resources, *[r.uid for r in resources] ) == resources
	assert service.filter_fetched( resources ) == []

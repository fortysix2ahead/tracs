
from pathlib import Path
from typing import cast

from pytest import mark, raises

from test.mock import Mock, MOCK_TYPE, MockActivity
from tracs.db import ActivityDb
from tracs.registry import Registry
from tracs.resources import Resource, ResourceType
from tracs.service import Service

def test_constructor():
	mock = Mock()

	assert mock.ctx is None
	assert mock.name == 'mock'
	assert mock.display_name == 'Mock'
	assert mock.enabled is True

	assert mock.config_value( 'test' ) is None
	assert mock.config_value( 'test', 10 ) == 10
	assert mock.state_value( 'test' ) is None
	assert mock.state_value( 'test', 10 ) == 10

	mock.set_config_value( 'test', 20 )
	assert mock.config_value( 'test' ) == 20
	mock.set_state_value( 'test', 30 )
	assert mock.state_value( 'test' ) == 30

	mock = Mock( name='MOCK', display_name='A Mock Service', enabled=False )
	assert mock.name == 'MOCK'
	assert mock.display_name == 'A Mock Service'
	assert mock.enabled is False

	# absolute paths work, even with MemFS
	r = Resource( uid='mock:1001', path='recording.gpx' )
	assert mock.path_for( r, absolute=True, as_path=False ) == '/mock/1/0/0/1001/recording.gpx'

@mark.service( cls=Mock )
def test_path_for( service ):
	# path for a given id
	assert service.path_for_id( '1001' ) == Path( '1/0/0/1001' )
	assert service.path_for_id( '1' ) == Path( '0/0/1/1' )
	assert service.path_for_id( '1001', 'test' ) == Path( 'test/1/0/0/1001' )
	assert service.path_for_id( '1001', resource_path='recording.gpx' ) == Path( '1/0/0/1001/recording.gpx' )
	assert service.path_for_id( '1001', 'test', 'recording.gpx' ) == Path( 'test/1/0/0/1001/recording.gpx' )

	# as str
	assert service.path_for_id( '1001', 'test', 'recording.gpx', as_path=False ) == 'test/1/0/0/1001/recording.gpx'

	# paths for resources
	r = Resource( uid='mock:1001', path='recording.gpx' )
	assert service.path_for( r, absolute=False ) == Path( 'mock/1/0/0/1001/recording.gpx' )
	assert service.path_for( r, absolute=False, omit_classifier=True ) == Path( '1/0/0/1001/recording.gpx' )
	assert service.path_for( r, absolute=False, as_path=False ) == 'mock/1/0/0/1001/recording.gpx'
	assert service.path_for( r, absolute=False, omit_classifier=True, as_path=False ) == '1/0/0/1001/recording.gpx'

	# absolute paths work, when there is an FS behind
	assert service.path_for( r, absolute=True, as_path=False ) == '/mock/1/0/0/1001/recording.gpx'
	assert service.path_for( r, absolute=True, omit_classifier=True, as_path=False ) == '/1/0/0/1001/recording.gpx'

@mark.service( cls=Mock, register=True )
def test_path_for_cls( service ):
	# path for a uid (this calls path_for_id internally)
	assert Service.path_for_uid( 'mock:1001' ) == Path( 'mock/1/0/0/1001' )
	assert Service.path_for_uid( 'mock:0' ) == Path( 'mock/0/0/0/0' )

	with raises( AttributeError ):
		assert Service.path_for_uid( 'unknown:1001' ) == Path( 'unknown/1/0/0/1001' )

@mark.context( env='empty', persist='clone', cleanup=True )
@mark.service( cls=Mock, init=True, register=True )
def test_fetch( service: Mock ):
	service.import_activities( skip_download=True, skip_link=True )
	assert len( service.ctx.db.activities ) == 3

	mfs = service.ctx.db_fs_for( service.name )
	assert mfs.exists( '1/0/0/1001/1001.json' )
	assert not mfs.exists( '1/0/0/1001/1001.gpx' )

	# test force flag
	mtime = mfs.getmodified( '1/0/0/1001/1001.json' )
	service.import_activities( skip_download=True, skip_link=True )
	assert mfs.getmodified( '1/0/0/1001/1001.json' ) == mtime
	service.import_activities( force=True, skip_download=True, skip_link=True )
	assert mfs.getmodified( '1/0/0/1001/1001.json' ) > mtime

	# test pretend flag
	mtime = mfs.getmodified( '1/0/0/1001/1001.json' )
	service.import_activities( force=True, pretend=True, skip_download=True, skip_link=True )
	assert mfs.getmodified( '1/0/0/1001/1001.json' ) == mtime

@mark.context( env='empty', persist='clone', cleanup=True )
@mark.service( cls=Mock, init=True, register=True )
def test_download( service ):
	service.import_activities( skip_download=False, skip_link=True )

	assert len( service.ctx.db.resources ) == 6
	assert len( service.ctx.db.activities ) == 3

	mfs = service.ctx.db_fs_for( service.name )
	assert mfs.exists( '1/0/0/1001/1001.gpx' )

@mark.context( env='empty', persist='clone', cleanup=True )
@mark.service( cls=Mock, init=True, register=True )
def test_filter_fetched( service ):
	resources = [
		Resource( uid='polar:10', path='10.gpx' ),
		Resource( uid='polar:20', path='20.gpx' ),
		Resource( uid='polar:30', path='30.gpx' ),
	]

	assert service.filter_fetched( resources, 'polar:20' ) == [resources[1]]
	assert service.filter_fetched( resources, 'polar:10', 'polar:20' ) == [resources[0], resources[1]]
	assert service.filter_fetched( resources, *[r.uid for r in resources] ) == resources
	assert service.filter_fetched( resources ) == []

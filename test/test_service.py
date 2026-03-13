
from pathlib import Path

from fs import open_fs
from fs.multifs import MultiFS
from pytest import mark

from test.mock import Mock
from tracs.constants import CFG_DB_FS, CFG_FS, CFG_TMP_FS
from tracs.resources import Resource
from tracs.uid import uid

default_cfg = {
	CFG_FS: open_fs( 'mem://' ),
	CFG_DB_FS: open_fs( 'mem://' ),
	CFG_TMP_FS: open_fs( 'mem://' ),
}

@mark.unit
def test_constructor( ctx ):
	mock = Mock( **default_cfg )
	assert mock.ctx is None
	assert mock.name == 'mock'
	assert mock.display_name == 'Mock'
	assert mock.enabled is True

	mock = Mock( name='MOCK', display_name='A Mock Service', user_id='user', enabled=False, **default_cfg )
	assert mock.name == 'MOCK'
	assert mock.display_name == 'A Mock Service'
	assert mock.enabled is False

	# absolute paths work, even with MemFS
	r = Resource( uid='mock:1001', path='recording.gpx' )
	assert mock.path_for( r, absolute=True, as_path=False ) == '/db/MOCK/user/1/0/0/1001/recording.gpx'

@mark.unit
@mark.service( cls=Mock, name='MOCK', display_name='Mock Service One', user_id='moo@example.com', path='m00h', takeout_path='take0uts/m00' )
def test_constructor_fixture( service ):
	assert service.name == 'MOCK'
	assert service.display_name == "Mock Service One"
	assert service._user_id == "moo@example.com"

	assert isinstance( service.fs, MultiFS )
	assert str( service.fs.write_fs ) == '<memfs>/db/m00h'
	assert str( service.base_fs ) == '<memfs>/db/m00h'
	assert str( service.overlay_fs ) == '<memfs>/overlay/m00h'
	assert str( service.takeout_fs ) == '<memfs>/takeouts/take0uts/m00'

@mark.unit
@mark.service( cls=Mock )
def test_path_for_id( service ):
	# splitting of an id to segments
	assert service.path_for_id( '1001' ) == '1/0/0/1001'
	assert service.path_for_id( '1' ) == '0/0/1/1'
	# provide base path: prepend
	assert service.path_for_id( '1001', base_path='test' ) == 'test/1/0/0/1001'
	# provide resource path: append at end
	assert service.path_for_id( '1001', resource_path='recording.gpx' ) == '1/0/0/1001/recording.gpx'
	# base + resource, without a user id
	assert service.path_for_id( '1001', base_path='test', resource_path='recording.gpx' ) == 'test/1/0/0/1001/recording.gpx'
	# base + user + resource
	assert service.path_for_id( '1001', 'test', 'user', 'recording.gpx' ) == 'test/user/1/0/0/1001/recording.gpx'

	# as path
	assert service.path_for_id( '1001', 'test', 'user', 'recording.gpx', as_path=True ) == Path( 'test/user/1/0/0/1001/recording.gpx' )

	# service path

	# base + user (not yet set) + resource
	assert service.svc_path_for_id( '1001', 'recording.gpx' ) == 'mock/1/0/0/1001/recording.gpx'

	service._name = 'MOCK'
	service._user_id = 'USER'
	assert service.svc_path_for_id( '1001', 'recording.gpx' ) == 'MOCK/USER/1/0/0/1001/recording.gpx'

@mark.unit
@mark.service( cls=Mock, user_id='user' )
def test_path_for( service ):
	assert service.name == 'mock' and service._user_id == 'user'

	# case 1: uid without a path + path in resource with filename only
	r = Resource( uid=uid( 'mock:1001' ), path='recording.gpx' )
	assert service.path_for( r ) == 'mock/user/1/0/0/1001/recording.gpx'
	assert service.path_for( r, absolute=False ) == 'mock/user/1/0/0/1001/recording.gpx' # absolute = False is the default
	# assert service.path_for( r, absolute=False, omit_classifier=True ) == '1/0/0/1001/recording.gpx'
	assert service.path_for( r, absolute=False, as_path=True ) == Path( 'mock/user/1/0/0/1001/recording.gpx' )
	# assert service.path_for( r, absolute=False, omit_classifier=True, as_path=False ) == '1/0/0/1001/recording.gpx'

	# case 2: uid without a path + path with parent dirs in resource
	r = Resource( uid=uid( 'mock:1001' ), path='mock/1/0/0/1001/recording.gpx' )
	assert service.path_for( r ) == 'mock/1/0/0/1001/recording.gpx'

	# case 3: uid with a file path + path in resource is empty
	r = Resource( uid=uid( 'mock:1001/recording.gpx' ) )
	assert service.path_for( r ) == 'mock/user/1/0/0/1001/recording.gpx'

	# case 4: uid with a path including dirs + path in resource is empty -> this should never happen, but works also
	r = Resource( uid=uid( 'mock:1001/mock/1/0/0/1001/recording.gpx' ) )
	assert service.path_for( r ) == 'mock/1/0/0/1001/recording.gpx'

	# case 5: uid without a path + absolute path in resource
	r = Resource( uid=uid( 'mock:1001' ), path='/usr/local/var/recording.gpx' )
	assert service.path_for( r ) == '/usr/local/var/recording.gpx'

	# absolute paths work differently when there is an OSFS behind, see next test case
	r = Resource( uid=uid( 'mock:1001' ), path='recording.gpx' )
	assert service.path_for( r, absolute=True ) == '/db/mock/user/1/0/0/1001/recording.gpx' # this is actually a relative path as there's no OSFS behind
	# absolute implies omit classifier
	# assert service.path_for( r, absolute=True, omit_classifier=True ) == '/db/mock/1/0/0/1001/recording.gpx'

@mark.unit
@mark.context( env='empty', persist='clone', cleanup=True )
@mark.service( cls=Mock )
def test_path_for_with_osfs( service ):
	dbpath = service.dbfs.getsyspath( '/' )
	r = Resource( uid='mock:1001', path='recording.gpx' )
	assert service.path_for( r, absolute=True ) == f'{dbpath}/mock/user/1/0/0/1001/recording.gpx'
	assert service.path_for( r, absolute=True, omit_classifier=True ) == f'{dbpath}/mock/user/1/0/0/1001/recording.gpx'

# noinspection PyTestUnpassedFixture
@mark.context( env='empty', persist='mem', cleanup=True )
@mark.service( cls=Mock, init=True, register=True )
def test_fetch( service: Mock ):
	service.import_activities( skip_download=True, skip_link=True, amount=3 )
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
	service.import_activities( skip_download=False, skip_link=True, amount=3 )

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

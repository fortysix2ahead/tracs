from datetime import datetime
from importlib.resources import path as pkgpath
from logging import getLogger
from os.path import dirname
from pathlib import Path
from shutil import copytree, rmtree
from typing import Any, Dict, Generator, List, NamedTuple, Optional, Tuple

from fs.base import FS
from fs.copy import copy_dir, copy_fs
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.subfs import SubFS
from fs.tempfs import TempFS
from pytest import fixture

from tracs.activity import Activity
from tracs.constants import CFG_CTX, CFG_FS, DB_DIRNAME
from tracs.context import ApplicationContext, set_current_ctx
from tracs.db import ActivityDb
from tracs.pluginmgr import PluginManager, Registry
from tracs.rules import RuleParser
from tracs.service import Service
from tracs.utils import FsPath
from test.helpers import get_db_as_json, get_file_as_json

log = getLogger( __name__ )

ENABLE_LIVE_TESTS = 'ENABLE_LIVE_TESTS'
PERSISTANCE_NAME = 'persistance_layer'

class Environment( NamedTuple ):
	ctx: ApplicationContext
	db: ActivityDb
	registry: Registry

def marker( request, name, key, default = None ):
	try:
		m = request.node.get_closest_marker( name )
		if key:
				return m.kwargs[key]
		elif not key:
			return m.args[0]

	except (AttributeError, IndexError, KeyError, TypeError):
		log.info( f'unable to access marker {name}.{key}, falling back to default value = {default}', exc_info=False )
		return default

def markers( request, name ):
	_keys = [ 'cls' ]
	m = request.node.get_closest_marker( name )
	_kwargs = { k: v for k, v in m.kwargs.items() if k not in _keys }
	return _kwargs

# shared fixtures

# old version which does work entirely as MemoryFS does not play well with SubFS
# we'll keep this, maybe we'll find a workaround later.
@fixture
def fs_v1( request ) -> Generator[FS, Any, None]:
	env = marker( request, 'context', 'env', 'empty' )
	persist = marker( request, 'context', 'persist', 'mem' )
	cleanup = marker( request, 'context', 'cleanup', True )

	with pkgpath( 'test', '__init__.py' ) as test_pkg_path:
		pkg_path = test_pkg_path.parent.parent
		env_path = f'{pkg_path}/test/environments/{env}'
		env_fs = OSFS( root_path=env_path )

		if persist in ['disk', 'clone', 'var']:
			var_path = f'{pkg_path}/var/run/{datetime.now().strftime( "%H%M%S_%f" )}'
			var_fs = OSFS( root_path=var_path, create=True )

			_fs = MultiFS()
			_fs.add_fs( 'underlay', env_fs, write=False )
			_fs.add_fs( 'overlay', var_fs, write=True )
			log.info( f'using {var_path} as FS write layer' )

		elif persist == 'mem':
			_fs = MultiFS()
			_fs.add_fs( 'underlay', env_fs, write=False )
			_fs.add_fs( 'overlay', MemoryFS(), write=True )
			log.info( f'using mem:// as FS write layer' )

		else:
			raise ValueError( 'value of key persist needs to be one of [mem, disk, clone]' )

	yield _fs

	if cleanup:
		overlay = _fs.get_fs( 'overlay' )
		if isinstance( overlay, OSFS ):
			sp = overlay.getsyspath( '/' )
			print( sp )
#			if dirname( dirname( sp ) ).endswith( 'var/run' ):  # sanity check: only remove when in var/run
#				overlay.remove( '/' )
			log.info( f'cleaned up temporary persistance dir {_fs.get_fs( "overlay" )}' )

# different version compared to fs_v1() above, using FS with disk backend only
# unfortunately this does also not work
@fixture
def fs_v2( request ) -> Generator[FS, Any, None]:
	env = marker( request, 'context', 'env', 'empty' )
	cleanup = marker( request, 'context', 'cleanup', True )

	with pkgpath( 'test', '__init__.py' ) as test_pkg_path:
		pkg_path = test_pkg_path.parent.parent
		env_path = f'{pkg_path}/test/environments/{env}'
		env_fs = OSFS( root_path=env_path )

		run_id = datetime.now().strftime( "_%y%m%d_%H%M%S_%f" )
		var_path = f'{pkg_path}/var/run'
		var_fs = TempFS( identifier=run_id, temp_dir=var_path, auto_clean=cleanup )

		_fs = MultiFS()
		_fs.add_fs( 'underlay', env_fs, write=False )
		_fs.add_fs( 'overlay', var_fs, write=True )
		log.info( f'using {var_path} as FS write layer' )

		yield _fs

		_fs.close() # close probably not necessary, temp fs is auto closed

# fs_v3, using copy and paste from source fs
@fixture
def fs_v3( request ) -> Generator[FS, Any, None]:
	env = marker( request, 'context', 'env', 'empty' )
	cleanup = marker( request, 'context', 'cleanup', True )

	with pkgpath( 'test', '__init__.py' ) as test_pkg_path:
		pkg_path = test_pkg_path.parent.parent
		env_path = f'{pkg_path}/test/environments/{env}'
		env_fs = OSFS( root_path=env_path )

		run_id = datetime.now().strftime( "_%y%m%d_%H%M%S_%f" )
		var_path = f'{pkg_path}/var/run'
		var_fs = TempFS( identifier=run_id, temp_dir=var_path, auto_clean=cleanup )

		copy_dir( env_fs, '/', var_fs, '/', preserve_time=True )
		log.info( f'using {var_fs} as FS write layer' )

		yield var_fs

		var_fs.close() # close probably not necessary, temp fs is auto closed

@fixture
def fs( request, fs_v3: FS ) -> FS:
	return fs_v3

@fixture
def dbfs( request, fs: FS ) -> FS:
	fs.makedirs( DB_DIRNAME, recreate=True )
	return SubFS( fs, DB_DIRNAME )

@fixture
def db_path( request, fs: FS ) -> Path:
	if isinstance( fs, OSFS ):
		path = Path( fs.getsyspath( DB_DIRNAME ) )
		path.mkdir( parents=True, exist_ok=True )
		return path
	else:
		raise ValueError
	#env = marker( request, 'context', 'env', 'empty' )
	#with pkgpath( 'test', '__init__.py' ) as test_pkg_path:
	#	yield Path( test_pkg_path.parent, f'environments/{env}/db' )

@fixture
def db( request, fs: FS ) -> ActivityDb:
	if isinstance( fs, OSFS ):
		db_fs = OSFS( root_path=fs.getsyspath( DB_DIRNAME ), create=True )
	elif isinstance( fs, MemoryFS ):
		db_fs = MemoryFS()
	elif isinstance( fs, MultiFS ):
		fs.makedir( DB_DIRNAME, recreate=True )
		db_fs = SubFS( fs, DB_DIRNAME )
	else:
		raise ValueError

	summary_types = marker( request, 'db', 'summary_types', [] )
	recording_types = marker( request, 'db', 'recording_types', [] )

	return ActivityDb( fs=db_fs, summary_types=summary_types, recording_types=recording_types )
	#db_path = Path( env_fs.getsyspath( '/' ), DB_DIRNAME )
	#yield ActivityDb( path=db_path, read_only=False )

@fixture
def ctx( request, fs: FS ) -> ApplicationContext:
	flag_keys = ['verbose', 'debug', 'json', 'force' ]
	flags = { k: marker( request, 'context', k, False ) for k in flag_keys }

	return set_current_ctx( ApplicationContext( config_fs=fs, lib_fs=fs, _cli_args=(), _cli_kwargs=flags ) )

@fixture
def plugin_mgr( request ) -> PluginManager:
	# this needs to be made configurable
	return PluginManager.inst().init( [], False )

@fixture
def registry( request, plugin_mgr: PluginManager, ctx: ApplicationContext ) -> Registry:
	reg = plugin_mgr.registry()

	# todo: make this configurable?
#	for vf in reg.virtual_fields:
#		Activity.VF().add( vf )

	return reg

@fixture
def env( request, ctx: ApplicationContext, db: ActivityDb, registry: Registry ) -> Environment:
	ctx._db = db
	ctx.registry = registry
	return Environment( ctx, db, registry )

@fixture
def json( request ) -> Optional[Dict]:
	if marker := request.node.get_closest_marker( 'db' ):
		template = marker.kwargs.get( 'template', 'empty' )
		return get_db_as_json( template )
	elif marker := request.node.get_closest_marker( 'file' ):
		return get_file_as_json( marker.args[0] )

@fixture
def path( request ) -> Optional[Path]:
	with pkgpath( 'test', '__init__.py' ) as test_path:
		if p := marker( request, 'file', None, None ):
			return Path( test_path.parent, p )
		else:
			return Path( test_path.parent )

@fixture
def fspath( request ) -> FsPath:
	with pkgpath( 'test', '__init__.py' ) as test_path:
		return FsPath( OSFS( root_path=str( test_path.parent ), create=False ), marker( request, 'file', None, None ) )

@fixture
def fs_path( request ) -> Tuple[FS, str]:
	with pkgpath( 'test', '__init__.py' ) as test_path:
		return OSFS( root_path=str( test_path.parent ), create=False ), marker( request, 'file', None, None )

@fixture
def service( request, env: Environment ) -> Optional[Service]:
	service_class = marker( request, 'service', 'cls', None )
	_kwargs = markers( request, 'service' )
	service = service_class( **{ CFG_CTX: env.ctx, **_kwargs } )

	register = marker( request, 'service', 'register', False )
	if register and service not in env.registry.services:
		env.registry.services.append( service )

	return service

@fixture
def keywords() -> List[str]:
	# load keywords plugin
	return list( Registry.instance().virtual_fields.keys() )

@fixture
def parser( request, registry: Registry ) -> RuleParser:
	return RuleParser( keywords=registry.keywords, normalizers=registry.normalizers )

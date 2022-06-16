
from datetime import datetime
from json import load
from pathlib import Path
from shutil import copy
from shutil import copytree

from importlib.resources import path
from shutil import rmtree
from typing import Dict
from typing import Mapping
from typing import Tuple

from tinydb.table import Document

from tracs.config import GlobalConfig
from tracs.db import ActivityDb

def prepare_environment( cfg_name: str = None, lib_name: str = None, db_name: str = None ) -> Tuple[Path, Path]:
	run_dir = _run_path()
	run_dir = Path( run_dir, f'{datetime.now().strftime( "%y%m%d_%H%M%S_%f" )}' )
	run_dir.mkdir()
	dot_dir = Path( run_dir, '.tracs' )
	dot_dir.mkdir()

	if cfg_name:
		cfg_path = get_config_path( cfg_name )
		copy( Path( cfg_path, 'config.yaml' ), run_dir )
		copy( Path( cfg_path, 'state.yaml' ), run_dir )

	if lib_name:
		# lib_path = get_lib_path( lib_name )
		lib_path = 'test'

	if db_name:
		db_path = get_db_path( db_name )
		copy( Path( db_path ), Path( dot_dir, 'db.json' ) )

	cfg_path = run_dir
	lib_path = run_dir

	return cfg_path, lib_path

def get_config_path( name: str, writable: bool = False ) -> Path:
	with path( 'test', '__init__.py' ) as test_path:
		config_path = Path( test_path.parent, 'configurations', name )
		if writable:
			writable_config_path = Path( _run_path(), f'cfg_{name}-{datetime.now().strftime( "%H%M%S_%f" )}' )
			copytree( config_path, writable_config_path )
			config_path = writable_config_path
		return config_path

def get_lib_path( name: str, writable: bool = False ) -> Path:
	with path( 'test.libraries', name ) as p:
		if not writable:
			return p
		else:
			dst_lib = Path( _run_path(), f'l_{name}-{datetime.now().strftime( "%H%M%S_%f" )}' )
			copytree( p, dst_lib )
			return dst_lib

def get_db_path( name: str, writable: bool = False ) -> Path:
	with path( 'test.databases', f'{name}.db.json' ) as p:
		if not writable:
			return p
		else:
			dst_db = Path( _run_path(), f'{name}-{datetime.now().strftime( "%y%m%d_%H%M%S_%f" )}.db.json' )
			copy( p, dst_db )
			return dst_db

def get_dbpath( template: str, name: str, writable: bool ) -> Tuple[Path, Path]:
	with path( 'test', '__init__.py' ) as p:
		template_path = Path( p.parent, 'databases', f'{template}.db.json' )
		if writable:
			db_path = Path( p.parent.parent, 'var', 'run', f'{datetime.now().strftime( "%H%M%S_%f" )}', name )
		else:
			db_path = template_path
	return template_path, db_path

def get_inmemory_db( db_template: str ) -> ActivityDb:
	"""
	Returns an in-memory db initialized from the provided template db.

	:param db_template: template db or None
	:return: in-memory db
	"""
	db_path = get_db_path( db_template, False ) if db_template else get_db_path( 'empty', False )
	return ActivityDb( path=db_path, pretend=True, cache=False )

def get_file_db( db_template: str='empty', db_name: str='db.json', writable=False ) -> ActivityDb:
	"""
	Returns a file-based db, based on the provided template.

	:param db_template:
	:param db_name: name of the db, defaults to db.json
	:param writable: if the db shall be writable or not
	:return: file-based db
	"""
	template_path, db_path = get_dbpath( db_template, db_name, writable )
	if template_path != db_path:
		db_path.parent.mkdir( parents=True, exist_ok=True )
		copy( template_path, db_path )

	return ActivityDb( path=db_path, pretend=False, cache=False )

def get_dbjson( db_name: str ) -> Dict:
	db_path = get_db_path( db_name, False )
	return load( open( db_path, 'r', encoding='utf8' ) )

def get_db_json( db_name: str, inmemory_db: bool = False ) -> Tuple[ActivityDb, Mapping]:
	writable = not inmemory_db
	db_path = get_db_path( db_name, writable )
	GlobalConfig.db = ActivityDb( db_path=db_path, writable=writable )
	json = load( open( get_db_path( db_name ), 'r', encoding='utf8' ) )
	return GlobalConfig.db, json

def get_db_as_json( db_name: str ):
	db_path = get_db_path( db_name, False )
	GlobalConfig.db = ActivityDb( db_path=db_path, writable=False )
	# return the json only
	return load( open( get_db_path( db_name ), 'r', encoding='utf8' ) )

def get_env( env_name: str ) -> Path:
	with path( 'test.environments', env_name ) as src_env:
		run_path = _run_path()
		dst_env = Path( run_path, f'run-{datetime.now().strftime( "%H%M%S_%f" )}' )
		copytree( src_env, dst_env )
		return dst_env

def get_file_path( rel_path: str ) -> Path:
	with path( 'test', '__init__.py' ) as test_path:
		return Path( test_path.parent, rel_path )

def _run_path() -> Path:
	with path( 'test', '__init__.py' ) as test_path:
		run_path = Path( test_path.parent, 'run', '_autorun' )
		if run_path.exists() and run_path.is_dir():
			return run_path
		else:
			run_path.unlink( missing_ok=True )
			run_path.mkdir( parents = True )
			return run_path

def var_run_path() -> Path:
	with path( 'test', '__init__.py' ) as test_pkg_path:
		run_path = Path( test_pkg_path.parent.parent, 'var', 'run', f'{datetime.now().strftime( "%H%M%S_%f" )}' )
		run_path.unlink( missing_ok=True )
		run_path.mkdir( parents=True )
		return run_path

def clean( db_dir: Path = None, db_path: Path = None ) -> None:
	if db_dir:
		rmtree( db_dir, ignore_errors=True )
	if db_path:
		db_path.unlink( missing_ok=True )

def ids( doc_list: [Document] ) -> []:
	return [a.doc_id for a in doc_list]

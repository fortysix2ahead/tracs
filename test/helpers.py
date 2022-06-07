
from datetime import datetime
from json import load
from pathlib import Path
from shutil import copy
from shutil import copytree

from importlib.resources import path
from typing import Mapping
from typing import Tuple

from tinydb.table import Document

from gtrac.config import ApplicationConfig as cfg
from gtrac.config import GlobalConfig
from gtrac.db import ActivityDb
from gtrac.service import Service
from gtrac.plugins.polar import Polar
from gtrac.plugins.strava import Strava
from gtrac.plugins.waze import Waze

def prepare_environment( cfg_name: str = None, lib_name: str = None, db_name: str = None ) -> Tuple[Path, Path]:
	run_dir = _run_path()
	run_dir = Path( run_dir, f'{datetime.now().strftime( "%y%m%d_%H%M%S_%f" )}' )
	run_dir.mkdir()
	dot_dir = Path( run_dir, '.gtrac' )
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
	with path( 'test.configurations', name ) as p:
		if not writable:
			return p
		else:
			dst_cfg = Path( _run_path(), f'cfg_{name}-{datetime.now().strftime( "%H%M%S_%f" )}' )
			copytree( p, dst_cfg )
			return dst_cfg

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

def get_db_json( db_name: str, inmemory_db: bool = False ) -> Tuple[ActivityDb, Mapping]:
	writable = not inmemory_db
	db_path = get_db_path( db_name, writable )
	GlobalConfig.db = ActivityDb( db_path=db_path, writable=writable )
	json = load( open( get_db_path( db_name ), 'r', encoding='utf8' ) )
	return GlobalConfig.db, json

def get_db_as_json( db_name: str ):
	# we need to load the db anyway as accessors are regsitered in there
	db_path = get_db_path( db_name, False )
	GlobalConfig.db = ActivityDb( db_path=db_path, writable=False )
	# return the json only
	return load( open( get_db_path( db_name ), 'r', encoding='utf8' ) )

def get_file_db() -> ActivityDb:
	db_path = Path( _run_path(), f'{datetime.now().strftime( "%y%m%d_%H%M%S_%f" )}.db.json' )
	return ActivityDb( db_path=db_path, services=[Polar, Strava, Waze] )

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

def ids( doc_list: [Document] ) -> []:
	return [a.doc_id for a in doc_list]

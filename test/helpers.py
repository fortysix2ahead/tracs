
from datetime import datetime
from json import load as load_json
from pathlib import Path
from shutil import copy
from shutil import copytree

from importlib.resources import path
from shutil import rmtree
from typing import Dict
from typing import Tuple

from tinydb.table import Document

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

def get_db_path( template_name: str, writable: bool = False ) -> Tuple[Path, Path, Path]:
	"""
	Creates/returns an existing db and returns a tuple consisting of [parent_path, db_path, meta_path]

	:param template_name: template db name
	:param writable: if True copies the template and creates new db in var/run, if False returns template directly
	:return: Tuple of [parent_path, db_path, meta_path]
	"""
	with path( 'test.databases', f'{template_name}.db.json' ) as p:
		if not writable:
			return p.parent, p, Path( p.parent, 'meta.json' )
		else:
			dest_dir = var_run_path()
			dest_db = Path( dest_dir, f'db.json' )
			dest_meta = Path( dest_dir, f'meta.json' )
			copy( p, dest_db )
			copy( Path( p.parent, 'meta.json' ), dest_meta )
			return dest_dir, dest_db, dest_meta

def get_readonly_db_path( template_name: str ) -> Tuple[Path, Path, Path]:
	return get_db_path( template_name, False )

def get_writable_db_path( template_name: str ) -> Tuple[Path, Path, Path]:
	return get_db_path( template_name, True )

def get_inmemory_db( db_template: str = 'empty' ) -> ActivityDb:
	"""
	Returns an in-memory db initialized from the provided template db.

	:param db_template: template db or None
	:return: in-memory db
	"""
	parent_path, db_path, meta_path = get_db_path( db_template, False )
	return ActivityDb( path=parent_path, db_name=db_path.name, pretend=True, cache=False )

def get_file_db( db_template: str = 'empty', writable = False ) -> ActivityDb:
	"""
	Returns a file-based db, based on the provided template.

	:param db_template:
	:param db_name: name of the db, defaults to db.json
	:param writable: if the db shall be writable or not
	:return: file-based db
	"""
	parent_path, db_path, meta_path = get_db_path( db_template, writable )
	return ActivityDb( path=parent_path, db_name=db_path.name, pretend=not writable, cache=False )

def get_db_as_json( db_name: str ) -> Dict:
	parent_path, db_path, meta_path = get_db_path( db_name, False )
	return load_json( open( db_path, 'r', encoding='utf8' ) )

def get_file_path( rel_path: str ) -> Path:
	with path( 'test', '__init__.py' ) as test_path:
		return Path( test_path.parent, rel_path )

def var_run_path( file_name = None ) -> Path:
	"""
	Creates a new directory/file in var/run directory. If the file_name is missing, the directory will be created and
	returned, otherwise only the file path will be returned and the parent dir will be created.

	:param file_name: file name
	:return: path
	"""
	with path( 'test', '__init__.py' ) as test_pkg_path:
		if file_name:
			run_path = Path( test_pkg_path.parent.parent, 'var', 'run', f'{datetime.now().strftime( "%H%M%S_%f" )}', file_name )
			run_path.parent.mkdir( parents=True, exist_ok=True )
		else:
			run_path = Path( test_pkg_path.parent.parent, 'var', 'run', f'{datetime.now().strftime( "%H%M%S_%f" )}' )
			run_path.mkdir( parents=True, exist_ok=True )
		return run_path

def clean( db_dir: Path = None, db_path: Path = None ) -> None:
	return

	if db_dir:
		rmtree( db_dir, ignore_errors=True )
	if db_path:
		db_path.unlink( missing_ok=True )

def ids( doc_list: [Document] ) -> []:
	return [a.doc_id for a in doc_list]

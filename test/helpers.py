
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from importlib.resources import path
from json import load as load_json
from pathlib import Path
from shutil import copy
from shutil import copytree
from shutil import rmtree
from typing import Dict
from typing import Optional
from typing import Tuple

from pytest import mark

from tracs.config import ApplicationContext
from tracs.config import DB_DIRNAME
from tracs.config import TAKEOUT_DIRNAME
from tracs.db import ActivityDb

DATABASES = 'databases'
LIBRARIES = 'libraries'
VAR = 'var'
VAR_RUN = 'var/run'

@dataclass
class DbPath:

	parent: Path = field()
	activities: Path = field( default=None )
	metadata: Path = field( default=None )
	resources: Path = field( default=None )
	schema: Path = field( default=None )

	def __post_init__( self ):
		if self.parent:
			self.activities = Path( self.parent, 'activities.json' )
			self.metadata = Path( self.parent, 'metadata.json' )
			self.resources = Path( self.parent, 'resources.json' )
			self.schema = Path( self.parent, 'schema.json' )

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

def prepare_context( config_name: Optional[str], lib_name: Optional[str], takeout_name: Optional[str] ) -> ApplicationContext:
	with path( 'test', '__init__.py' ) as test_path:
		test_path = test_path.parent
		target_path = var_run_path()

		if config_name:
			config_src_path = Path( test_path, 'configurations', config_name )
			copytree( config_src_path, target_path, dirs_exist_ok=True )

		if lib_name:
			lib_src_path = Path( test_path, 'libraries', lib_name )
			copytree( lib_src_path, Path( target_path, DB_DIRNAME ), dirs_exist_ok=True )

		if takeout_name:
			takeout_src_path = Path( test_path, 'takeouts', takeout_name )
			copytree( takeout_src_path, Path( target_path, TAKEOUT_DIRNAME ), dirs_exist_ok=True )

		config_dir = str( target_path )
		config_file = f'{config_dir}/config.yaml'
		lib_dir = config_dir
		db_dir = Path( lib_dir, DB_DIRNAME )

		return ApplicationContext( configuration=config_file, library=lib_dir, db=ActivityDb( path=db_dir ), verbose=True )

def get_config_path( name: str, writable: bool = False ) -> Path:
	with path( 'test', '__init__.py' ) as test_path:
		config_path = Path( test_path.parent, 'configurations', name )
		if writable:
			writable_config_path = Path( _run_path(), f'cfg_{name}-{datetime.now().strftime( "%H%M%S_%f" )}' )
			copytree( config_path, writable_config_path )
			config_path = writable_config_path
		return config_path

def get_db_path( template_name: str = None, library_name: str = None, read_only: bool = False ) -> DbPath:
	"""
	Creates/returns an existing db and returns a tuple consisting of [parent_path, db_path, meta_path]

	:param template_name: template db name
	:return: Tuple of [parent_path, db_path, meta_path]
	"""
	with path( 'test', '__init__.py' ) as p:
		if template_name:
			db_path = DbPath( parent = Path( p.parent, DATABASES, template_name ) )
		elif library_name:
			db_path = DbPath( parent = Path( p.parent, LIBRARIES, library_name ) )

		if read_only:
			return db_path
		else:
			dest_path = var_run_path()
			dest_path.mkdir( exist_ok=True )
			copytree( db_path.parent, dest_path, dirs_exist_ok=True )
			return DbPath( dest_path )

def get_db( template: str = None, read_only: bool = False ) -> Optional[ActivityDb]:
	"""
	Returns an in-memory db initialized from the provided template db.

	:param template: template db or None
	:param read_only: read_only flag
	:return: db
	"""
	db_path = get_db_path( template_name=template, read_only=read_only )
	return ActivityDb( path=db_path.parent, read_only=read_only )

def get_inmemory_db( template: str = None, library: str = None ) -> Optional[ActivityDb]:
	"""
	Returns an in-memory db initialized from the provided template db.

	:param template: template db or None
	:param library: optional lib name
	:return: in-memory db
	"""
	if library:
		db_path = get_db_path( library_name=library, writable=False )
	elif template:
		db_path = get_db_path( template_name=template, writable=False )
	else:
		return None

	return ActivityDb( path=db_path.parent, pretend=True )

def get_file_db( template: str = None, library: str = None, writable = False ) -> ActivityDb:
	"""
	Returns a file-based db, based on the provided template.

	:param template:
	:param library:
	:param writable: if the db shall be writable or not
	:return: file-based db
	"""
	if library:
		db_path = get_db_path( library_name=library, writable=writable )
	else:
		db_path = get_db_path( template_name=template, writable=writable )

	return ActivityDb( path=db_path.parent, pretend=not writable )

def get_db_as_json( db_name: str ) -> Dict:
	parent_path, db_path, meta_path = get_db_path( db_name, writable=False )
	return load_json( open( db_path, 'r', encoding='utf8' ) )

def get_file_as_json( rel_path: str ) -> Dict:
	json_path = get_file_path( rel_path )
	return load_json( open( json_path, 'r', encoding='utf8' ) )

def get_file_path( rel_path: str ) -> Path:
	"""
	Provides a path relative to $PROJECT_DIR/test.

	:param rel_path: relative path
	:return: path relative to the /var/run directory
	"""
	with path( 'test', '__init__.py' ) as test_path:
		return Path( test_path.parent, rel_path )

def get_var_path( rel_path: str ) -> Path:
	"""
	Provides a path relative to $PROJECT_DIR/var.

	:param rel_path: relative path
	:return: path relative to the var directory
	"""
	with path( 'test', '__init__.py' ) as test_path:
		return Path( test_path.parent.parent, VAR, rel_path )

def get_var_run_path( rel_path: str ) -> Path:
	"""
	Provides a path relative to $PROJECT_DIR/var/run.

	:param rel_path: relative path
	:return: path relative to the var/run directory
	"""
	with path( 'test', '__init__.py' ) as test_path:
		return Path( test_path.parent.parent, VAR_RUN, rel_path )

def var_run_path( file_name = None ) -> Path:
	"""
	Creates a new directory/file in var/run directory. If the file_name is missing, the directory will be created and
	returned, otherwise only the file path will be returned and the parent dir will be created.

	:param file_name: file name
	:return: path
	"""
	with path( 'test', '__init__.py' ) as test_pkg_path:
		if file_name:
			run_path = Path( test_pkg_path.parent.parent, VAR_RUN, f'{datetime.now().strftime( "%H%M%S_%f" )}', file_name )
			run_path.parent.mkdir( parents=True, exist_ok=True )
		else:
			run_path = Path( test_pkg_path.parent.parent, VAR_RUN, f'{datetime.now().strftime( "%H%M%S_%f" )}' )
			run_path.mkdir( parents=True, exist_ok=True )
		return run_path

def cleanup( run_path: Path = None ) -> None:
	if run_path and run_path.parent.name == 'run' and run_path.parent.parent.name == 'var': # sanity check: only remove when in test/var/run
		rmtree( run_path, ignore_errors=True )

skip_live = mark.skipif(
	not ( get_var_path( 'config_live.yaml' ).exists() and get_var_path( 'state_live.yaml' ).exists() ), reason="live test not enabled as configuration is missing"
)

# mock gpx resource

gpx_resource = '''
<?xml version="1.0" encoding="UTF-8"?>
<gpx xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"
    xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v2" version="1.1" creator="Pocket Earth v2.8"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns="http://www.topografix.com/GPX/1/1">
    <metadata>
        <name>Skaftafell - Vatnajökull</name>
        <link href="http://www.geomagik.com">
            <text>GeoMagik LLC</text>
        </link>
        <time>2015-08-02T12:16:20Z</time>
    </metadata>
    <trk>
        <name>Skaftafell - Vatnajökull</name>
        <trkseg>
            <trkpt lat="64.0162580" lon="-16.9656560">
                <ele>93.00</ele>
                <time>2015-07-27T17:40:56Z</time>
            </trkpt>
            <trkpt lat="64.0162390" lon="-16.9656320">
                <ele>93.00</ele>
                <time>2015-07-27T17:40:57Z</time>
            </trkpt>
            <trkpt lat="64.0162460" lon="-16.9656300">
                <ele>94.00</ele>
                <time>2015-07-27T17:40:58Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
'''

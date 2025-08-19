from datetime import datetime
from logging import getLogger
from re import compile
from typing import List

from attrs import define, field
from cattrs.preconf.orjson import make_converter
from fs.base import FS
from fs.copy import copy_dir
from fs.walk import Walker
from orjson import dumps, loads, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS
from rich.prompt import Confirm
from tracs.activity import Activities

log = getLogger( __name__ )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

ACTIVITIES_NAME = 'activities.json'
ACTIVITIES_PATH = f'/{ACTIVITIES_NAME}'
RESOURCES_NAME = 'resources.json'
RESOURCES_PATH = f'/{RESOURCES_NAME}'
SCHEMA_NAME = 'schema.json'
SCHEMA_PATH = f'/{SCHEMA_NAME}'

SCHEMA_CONVERTER = make_converter()

# activity handling

def load_activities( fs: FS ) -> Activities:
	try:
		activities = Activities.from_dict( loads( fs.readbytes( ACTIVITIES_PATH ) ) )
		log.debug( f'loaded {len( activities )} activities from {ACTIVITIES_NAME}' )
		return activities
	except RuntimeError:
		log.error( f'error loading db', exc_info=True )

def write_activities( activities: Activities, fs: FS ) -> None:
	fs.writebytes( ACTIVITIES_PATH, dumps( activities.to_dict(), option=ORJSON_OPTIONS ) )
	log.debug( f'wrote {len( activities )} activities to {ACTIVITIES_NAME}' )

def write_activities_as_list( activities: Activities ) -> List:
	return activities.to_dict()

# schema handling

@define
class Schema:

	version: int = field( default=None )

def load_schema( fs: FS ) -> Schema:
	schema = SCHEMA_CONVERTER.loads( fs.readbytes( SCHEMA_PATH ), Schema )
	log.debug( f'loaded database schema from {SCHEMA_PATH}, schema version = {schema.version}' )
	return schema

# backup & restore

def backup_db( db_fs: FS, backup_fs: FS ) -> None:
	backup_folder = datetime.utcnow().strftime( '%y%m%d_%H%M%S' )
	walker = Walker( filter=[ '*.json' ], exclude_dirs=[ '*' ], max_depth=0 )
	copy_dir( db_fs, '/', backup_fs, backup_folder, walker=walker, preserve_time=True )
	ctx().console.print( f'created database backup in {backup_fs.getsyspath( backup_folder )}' )

def restore_db( db_fs: FS, backup_fs: FS, force: bool = False ) -> None:
	try:
		rx = compile( r'/\d{6}_\d{6}' )
		dirs = list( Walker( max_depth=0 ).dirs( backup_fs, '/' ) )
		dirs = sorted( [ d for d in dirs if rx.fullmatch( d ) ] )
		backup_folder = dirs[-1]
		if force or Confirm.ask( f'Restore database from {backup_fs.getsyspath( backup_folder )}? The current state will be overwritten.' ):
			walker = Walker( filter=['*.json'], exclude_dirs=['*'], max_depth=0 )
			copy_dir( backup_fs, backup_folder, db_fs, '/', walker=walker, preserve_time=True )
			ctx().console.print( f'database restored from {backup_fs.getsyspath( backup_folder )}' )
	except RuntimeError:
		log.error( 'failed to restore backup', exc_info=True )

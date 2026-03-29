from datetime import datetime, timedelta
from logging import getLogger
from re import compile
from typing import List, Optional, Type

from attrs import define, field
from cattrs import Converter
from cattrs.preconf.orjson import OrjsonConverter
from fs.base import FS
from fs.copy import copy_dir
from fs.errors import FileExpected, ResourceNotFound
from fs.walk import Walker
from orjson import dumps, loads
from orjson.orjson import JSONDecodeError
from rich.prompt import Confirm

from tracs.activity import Activities, Activity, ActivityGroup, MultipartActivity
from tracs.activity_types import ActivityTypes
from tracs.constants import ACTIVITIES_PATH, GROUPS_PATH, MULTIPARTS_PATH, ORJSON_OPTIONS, SCHEMA_PATH
from tracs.resources import Resource, Resources
from tracs.uid import str_to_uid, UID, uid_to_str
from tracs.utils import fromisoformat, str_to_timedelta, timedelta_to_str, toisoformat

log = getLogger( __name__ )

# note:
# structure(data, Class)	== Deserialize
# unstructure(obj) == Serialize

# custom i/o handling

def resources_to_list( resources: Resources ) -> List[Resource]:
	return [ converter.unstructure( r ) for r in resources ]

def list_to_resources( resources: List[Resource], cls: Optional[Type] = None ) -> Resources:
	return Resources( lst=[converter.structure( r, Resource ) for r in resources] )

def activities_to_list( activities: Activities ) -> List[Activity]:
	return [ converter.unstructure( a ) for a in activities ]

def list_to_activities( activities: List[Activity], cls: Optional[Type] = None ) -> Activities:
	return Activities( lst=[converter.structure( a, Activity ) for a in activities], skip_checks=True )

def make_converter() -> Converter:
	c = OrjsonConverter( omit_if_default=True )

	c.register_unstructure_hook( datetime, toisoformat )
	c.register_unstructure_hook( timedelta, timedelta_to_str )
	c.register_unstructure_hook( UID, uid_to_str )
	c.register_unstructure_hook( ActivityTypes, lambda at: ActivityTypes.to_str( at ) )
	c.register_unstructure_hook( Resources, resources_to_list )
	c.register_unstructure_hook( Activities, activities_to_list )

	c.register_structure_hook( datetime, fromisoformat )
	c.register_structure_hook( timedelta, str_to_timedelta )
	c.register_structure_hook( ActivityTypes, lambda at, t: ActivityTypes.from_str( at ) )
	c.register_structure_hook( UID, str_to_uid )
	c.register_structure_hook( Resources, list_to_resources )
	c.register_structure_hook( Activities, list_to_activities )

	return c

converter = make_converter()

# activity handling

def _load_activities( fs: FS, path: str, cls: Type ) -> Activities:
	"""
	Loads activities from a provided file
	:param fs: file system to load from
	:param path: path to load from
	:return: loaded activities
	"""
	log.debug( f'loading activities from {path} in {fs}' )

	try:
		_bytes = fs.readbytes( path )
		_dicts = loads( _bytes )
		_activities = converter.structure( _dicts, cls )
		log.debug( f'loaded {len( _activities )} activities from {path}' )
	except (FileExpected, ResourceNotFound, JSONDecodeError):
		log.error( f'error loading activities', exc_info=True )
		_activities = Activities()

	return _activities

def load_activities( fs: FS ) -> Activities:
	_activities = Activities()

	# load regular activities
	_activities.add( lst=_load_activities( fs, ACTIVITIES_PATH, List[Activity] ), skip_checks=True )
	# load groups
	_activities.add( lst=_load_activities( fs, GROUPS_PATH, List[ActivityGroup] ), skip_checks=True )
	# load multiparts
	_activities.add( lst=_load_activities( fs, MULTIPARTS_PATH, List[MultipartActivity] ), skip_checks=True )

	return _activities

def write_activities( activities: Activities, fs: FS ) -> None:
	_activities = Activities( *sorted( activities.iter_regular(), key=lambda a: a.id ), skip_checks=True )
	fs.writebytes( ACTIVITIES_PATH, dumps( converter.unstructure( _activities ), option=ORJSON_OPTIONS ) )

	log.debug( f'wrote {len( _activities )} activities to {ACTIVITIES_PATH}' )

	_activities = Activities( *sorted( activities.iter_groups(), key=lambda a: a.id ), skip_checks=True )
	fs.writebytes( GROUPS_PATH, dumps( converter.unstructure( _activities ), option=ORJSON_OPTIONS ) )

	log.debug( f'wrote {len( _activities )} activities to {GROUPS_PATH}' )

	_activities = Activities( *sorted( activities.iter_multiparts(), key=lambda a: a.id ), skip_checks=True )
	fs.writebytes( MULTIPARTS_PATH, dumps( converter.unstructure( _activities ), option=ORJSON_OPTIONS ) )

	log.debug( f'wrote {len( _activities )} activities to {MULTIPARTS_PATH}' )

# schema handling

@define
class Schema:

	version: int = field( default=None )

def load_schema( fs: FS ) -> Schema:
	schema = converter.structure( loads( fs.readbytes( SCHEMA_PATH ) ), Schema )
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

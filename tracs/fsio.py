from datetime import datetime, time, timedelta
from logging import getLogger
from re import compile
from typing import List, Union

from attrs import define, field
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override
from cattrs.preconf.orjson import make_converter
from fs.base import FS
from fs.copy import copy_dir
from fs.walk import Walker
from orjson import OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS
from rich.prompt import Confirm

from tracs.activity import Activities, Activity, ActivityPart
from tracs.activity_types import ActivityTypes
from tracs.config import current_ctx as ctx
from tracs.core import Metadata
from tracs.resources import Resource, Resources
from tracs.uid import UID
from tracs.utils import fromisoformat, str_to_timedelta, timedelta_to_str

log = getLogger( __name__ )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

ACTIVITIES_NAME = 'activities.json'
ACTIVITIES_PATH = f'/{ACTIVITIES_NAME}'
RESOURCES_NAME = 'resources.json'
RESOURCES_PATH = f'/{RESOURCES_NAME}'
SCHEMA_NAME = 'schema.json'
SCHEMA_PATH = f'/{SCHEMA_NAME}'

ACTIVITIES_CONVERTER = make_converter()
RESOURCE_CONVERTER = make_converter()
CONVERTER = make_converter() # todo: is it possible to use only one cattr converter?
SCHEMA_CONVERTER = make_converter()

# converter configuration

# support for structuring

metadata_struct_hook = make_dict_structure_fn( Metadata, CONVERTER )
#activity_struct_hook = make_dict_structure_fn( Activity, CONVERTER, metadata = override( struct_hook=metadata_struct_hook ) ) # don't need this here ...
activity_struct_hook = make_dict_structure_fn( Activity, CONVERTER )

# support for unstructuring

metadata_unstruct_hook = make_dict_unstructure_fn(
	Metadata,
	CONVERTER,
	_cattrs_omit_if_default=True,
)

activity_part_unstruct_hook = make_dict_unstructure_fn(
	ActivityPart,
	CONVERTER,
	_cattrs_omit_if_default=True,
	__uids__=override( omit=True ),
)

# still don't understand why we need to define unstruct_hooks here, otherwise it will ignore _cattrs_omit_if_default
activity_unstruct_hook = make_dict_unstructure_fn(
	Activity,
	CONVERTER,
	_cattrs_omit_if_default=True,
	duration=override( unstruct_hook=timedelta_to_str ),
	duration_moving=override( unstruct_hook=timedelta_to_str ),
	metadata=override( unstruct_hook=metadata_unstruct_hook ),
	__uid__=override( omit=True ),
	__uids__=override( omit=True ),
	__dirty__=override( omit=True ),
	__parts__=override( omit=True ),
	__resources__=override( omit=True ),
	__parent__=override( omit=True ),
	__parent_id__=override( omit=True ),
	others=override( omit=True ),
	other_parts=override( omit=True ),

)

# activity structuring

ACTIVITIES_CONVERTER.register_structure_hook( time, lambda obj, cls: fromisoformat( obj ) )
ACTIVITIES_CONVERTER.register_structure_hook( timedelta, lambda obj, cls: str_to_timedelta( obj ) )

activity_structure_hook = make_dict_structure_fn(
	Activity,
	ACTIVITIES_CONVERTER,
	_cattrs_forbid_extra_keys=True,
)

ACTIVITIES_CONVERTER.register_structure_hook( ActivityTypes, lambda obj, cls: ActivityTypes.from_str( obj ) )

# activity unstructuring

ACTIVITIES_CONVERTER.register_unstructure_hook( timedelta, timedelta_to_str )
ACTIVITIES_CONVERTER.register_unstructure_hook( ActivityTypes, ActivityTypes.to_str )

activity_part_unstructure_hook = make_dict_unstructure_fn(
	ActivityPart,
	ACTIVITIES_CONVERTER,
	_cattrs_omit_if_default=True,
	__uids__=override( omit=True ),
)

ACTIVITIES_CONVERTER.register_unstructure_hook( ActivityPart, activity_part_unstructure_hook )

activity_unstructure_hook = make_dict_unstructure_fn(
	Activity,
	ACTIVITIES_CONVERTER,
	_cattrs_omit_if_default=True,
	__uid__=override( omit=True ),
	__uids__=override( omit=True ),
	__dirty__=override( omit=True ),
	__metadata__=override( omit=False, rename='metadata', unstruct_hook=metadata_unstruct_hook ),
	__parts__=override( omit=True ),
	__resources__=override( omit=True ),
	__parent__=override( omit=True ),
	__parent_id__=override( omit=True ),
	others=override( omit=True ),
	other_parts=override( omit=True ),

)

ACTIVITIES_CONVERTER.register_unstructure_hook( Activity, activity_unstructure_hook )

# resource

resource_structure_hook = make_dict_structure_fn(
	Resource,
	RESOURCE_CONVERTER,
	_cattrs_forbid_extra_keys=True,
)

RESOURCE_CONVERTER.register_structure_hook( Union[str, UID], lambda obj, cls: obj ) # uid should always be a str, so return the obj untouched

resource_unstructure_hook = make_dict_unstructure_fn(
	Resource,
	RESOURCE_CONVERTER,
	_cattrs_omit_if_default=True,
	content=override( omit=True ),
	data=override( omit=True ),
	raw=override( omit=True ),
	resources=override( omit=True ),
	status=override( omit=True ),
	summary=override( omit=True ),
	text=override( omit=True ),
	__parents__=override( omit=True ),
	__uid__=override( omit=True ),
)

RESOURCE_CONVERTER.register_unstructure_hook( Resource, resource_unstructure_hook )

# unified converter

# CONVERTER.register_structure_hook( time, lambda obj, cls: fromisoformat( obj ) )
CONVERTER.register_structure_hook( timedelta, lambda obj, cls: str_to_timedelta( obj ) )
CONVERTER.register_structure_hook( Metadata, metadata_struct_hook )
CONVERTER.register_structure_hook( ActivityTypes, lambda obj, cls: ActivityTypes.from_str( obj ) )
CONVERTER.register_structure_hook( Activity, activity_struct_hook )

CONVERTER.register_unstructure_hook( timedelta, timedelta_to_str )
# CONVERTER.register_unstructure_hook( datetime, lambda v: v.isoformat() if v else None )
CONVERTER.register_unstructure_hook( Metadata, metadata_unstruct_hook )
CONVERTER.register_unstructure_hook( ActivityTypes, ActivityTypes.to_str )
CONVERTER.register_unstructure_hook( ActivityPart, activity_part_unstruct_hook )
CONVERTER.register_unstructure_hook( Activity, activity_unstruct_hook )

# resource handling

def load_resources( fs: FS ) -> Resources:
	try:
		resources = RESOURCE_CONVERTER.loads( fs.readbytes( RESOURCES_PATH ), List[Resource] )
		log.debug( f'loaded {len( resources )} resource entries from {RESOURCES_NAME}' )
		return Resources( data = resources )
	except RuntimeError:
		log.error( f'error loading db', exc_info=True )

def write_resources( resources: Resources, fs: FS ) -> None:
	fs.writebytes( RESOURCES_PATH, RESOURCE_CONVERTER.dumps( resources.all( sort=True ), unstructure_as=List[Resource], option=ORJSON_OPTIONS ) )
	log.debug( f'wrote {len( resources )} resource entries to {RESOURCES_NAME}' )

# activity handling

def load_activities( fs: FS ) -> Activities:
	try:
		activities = CONVERTER.loads( fs.readbytes( ACTIVITIES_PATH ), List[Activity] )
		log.debug( f'loaded {len( activities )} activities from {ACTIVITIES_NAME}' )
		return Activities( data = activities )
	except RuntimeError:
		log.error( f'error loading db', exc_info=True )

def write_activities( activities: Activities, fs: FS ) -> None:
	dump = CONVERTER.dumps( activities.all( sort=True ), unstructure_as=List[Activity], option=ORJSON_OPTIONS )
	fs.writebytes( ACTIVITIES_PATH, dump )
	log.debug( f'wrote {len( activities )} activities to {ACTIVITIES_NAME}' )

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

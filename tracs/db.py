
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import chain
from logging import getLogger
from pathlib import Path
from shutil import copytree
from sys import exit as sysexit
from typing import cast, Dict, List, Optional, Union

from click import confirm
from dataclass_factory import Factory, Schema as DataclassFactorySchema
from fs.base import FS
from fs.copy import copy_file, copy_file_if
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from orjson import dumps, loads, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS
from rich import box
from rich.pretty import pretty_repr as pp
from rich.table import Table as RichTable

from tracs.activity import Activity, ActivityPart
from tracs.activity_types import ActivityTypes
from tracs.config import ApplicationContext
from tracs.migrate import migrate_db, migrate_db_functions
from tracs.registry import Registry
from tracs.resources import Resource, ResourceType
from tracs.rules import parse_rules

log = getLogger( __name__ )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

ACTIVITIES_NAME = 'activities.json'
INDEX_NAME = 'index.json'
METADATA_NAME = 'metadata.json'
RESOURCES_NAME = 'resources.json'
SCHEMA_NAME = 'schema.json'

DB_FILES = {
	ACTIVITIES_NAME: '{}',
	INDEX_NAME: '{}',
	METADATA_NAME: '{}',
	RESOURCES_NAME: '{}',
	SCHEMA_NAME: '{"version": 12}'
}

UNDERLAY = 'underlay'
OVERLAY = 'overlay'

@dataclass
class Schema:

	version: int = field( default_factory=dict )
	unknown: Dict = field( default_factory=dict )

	@classmethod
	def schema( cls ) -> DataclassFactorySchema:
		return DataclassFactorySchema( skip_internal=True, unknown='unknown' )

class IdSchema( DataclassFactorySchema ):

	def __init__(self):
		super().__init__( pre_parse=IdSchema.pre_parse, pre_serialize=IdSchema.pre_serialize )

	@classmethod
	def pre_parse( cls, data: Dict[str, Dict] ) -> Dict[str, Dict]:
		for k in data.keys():
			data[k]['id'] = int( k )
		return data

	@classmethod
	def pre_serialize( cls, data: Dict[int, Union[Activity,Resource]] ) -> Dict[int, Union[Activity,Resource]]:
		for item in data.values():
			item.id = None
		return data

class ActivityDb:

	def __init__( self, path: Optional[Path] = None, read_only: bool = False ):
		"""
		Creates an activity db, consisting of tiny db instances (meta + activities + resources + schema).

		:param path: directory containing db files
		:param read_only: read-only mode - does not allow write operations
		"""

		self._db_path = path
		self._read_only = read_only

		# initialize db file system(s)
		self._init_db_filesystem()

		# initialize db factory
		self._init_db_factory()

		# load content from disk
		self._load_db()

		# experimental: setup relations between resources and activities
		self._relate()

		# index
		# self._index = DbIndex( self._activities, self._resources )

	def _init_db_filesystem( self ):
		self.dbfs = MultiFS() # multi fs composed of os/memory + memory

		# operating system fs as underlay (resp. memory when no path is provided)
		if self._db_path:
			if self._read_only:
				self._init_readonly_filesystem( self.dbfs, self._db_path )
			else:
				self._init_filesystem( self.dbfs, self._db_path )

		else:
			self._init_inmemory_filesystem( self.dbfs )

	def _init_filesystem( self, dbfs: MultiFS, os_path: Path ):
		self._db_path.mkdir( parents=True, exist_ok=True )
		self.osfs = OSFS( root_path=str( self._db_path ) )
		dbfs.add_fs( UNDERLAY, OSFS( root_path=str( self._db_path ) ), write=False )
		dbfs.add_fs( OVERLAY, MemoryFS(), write=True )

		for file, content in DB_FILES.items():
			if not self.underlay_fs.exists( f'/{file}' ):
				self.underlay_fs.writetext( f'/{file}', content )
			# copy_file_if( self.pkgfs, f'/{f}', self.underlay_fs, f'/{f}', 'not_exists', preserve_time=True )

		# todo: this is probably not needed?
		for f in DB_FILES.keys():
			copy_file( self.underlay_fs, f'/{f}', self.overlay_fs, f'/{f}', preserve_time=True )

	def _init_readonly_filesystem( self, dbfs: MultiFS, os_path: Path ):
		if not os_path.exists():
			log.error( f'error opening db from {self._db_path} in read-only mode: path does not exist' )
			sysexit( -1 )

		self.osfs = OSFS( root_path=str( self._db_path ) )
		dbfs.add_fs( UNDERLAY, MemoryFS(), write=False )
		dbfs.add_fs( OVERLAY, MemoryFS(), write=True )

		for f in DB_FILES.keys():
			copy_file( self.osfs, f'/{f}', self.underlay_fs, f'/{f}', preserve_time=True )

	# for development only ...
	def _init_inmemory_filesystem( self, dbfs: MultiFS ):
		dbfs.add_fs( UNDERLAY, MemoryFS(), write=False )
		dbfs.add_fs( OVERLAY, MemoryFS(), write=True )

		for file, content in DB_FILES.items():
			self.underlay_fs.writetext( f'/{file}', content )

	def _init_db_factory( self ):
		self._factory = Factory(
			debug_path=True,
			schemas={
				# name_mapping={}
				Activity: Activity.schema(),
				ActivityPart: DataclassFactorySchema( omit_default=True, skip_internal=True, unknown='unknown' ),
				ActivityTypes: DataclassFactorySchema( parser=ActivityTypes.from_str, serializer=ActivityTypes.to_str ),
				Resource: Resource.schema(),
				Schema: Schema.schema(),
				Dict[int, Activity]: IdSchema(),
				Dict[int, Resource]: IdSchema(),
			}
		)

	def _load_db( self ):
		json = loads( self.dbfs.readbytes( SCHEMA_NAME ) )
		self._schema = self._factory.load( json, Schema )

		json = loads( self.dbfs.readbytes( RESOURCES_NAME ) )
		self._resources = self._factory.load( json, Dict[int, Resource] )

		json = loads( self.dbfs.readbytes( ACTIVITIES_NAME ) )
		self._activities = self._factory.load( json, Dict[int, Activity] )

	def _relate( self ):
		for r in self.resources:
			a = self.get_by_uid( r.uid )
			a.__resources__.append( r )
			r.__parent_activity__ = a

	def commit( self, do_commit: bool = True ):
		if do_commit:
			self.commit_resources()
			self.commit_activities()

	def commit_activities( self ):
		json = self._keys_to_str( self._factory.dump( self._activities, Dict[int, Activity] ) )
		self.overlay_fs.writebytes( f'/{ACTIVITIES_NAME}', dumps( json, option=ORJSON_OPTIONS ) )

	def commit_resources( self ):
		json = self._keys_to_str( self._factory.dump( self._resources, Dict[int, Resource] ) )
		self.overlay_fs.writebytes( f'/{RESOURCES_NAME}', dumps( json, option=ORJSON_OPTIONS ) )

	# replace int keys with strings ... :-( todo: how to get around this?
	# noinspection PyMethodMayBeStatic
	def _keys_to_str( self, mapping: Dict ) -> Dict:
		for key in [ k for k in mapping.keys() ]:
			mapping[str( key )] = mapping.pop( key )
		return mapping

	def save( self ):
		if self._read_only or self.underlay_fs is None:
			return
		for f in DB_FILES:
			copy_file_if( self.overlay_fs, f'/{f}', self.underlay_fs, f'/{f}', 'newer' )

	def close( self ):
		# self.commit() # todo: really do auto-commit here?
		self.save()

	# ---- DB Properties --------------------------------------------------------

	@property
	def underlay_fs( self ) -> FS:
		return self.dbfs.get_fs( UNDERLAY )

	@property
	def overlay_fs( self ) -> FS:
		return self.dbfs.get_fs( OVERLAY )

	@property
	def factory( self ) -> Factory:
		return self._factory

	@property
	def schema( self ) -> Schema:
		return self._schema

	# path properties

	@property
	def path( self ) -> Path:
		return self._activities_path.parent

	@property
	def db_path( self ) -> Path:
		return self._activities_path

	@property
	def activities_path( self ) -> Path:
		return self._activities_path

	@property
	def resources_path( self ) -> Path:
		return self._resources_path

	@property
	def metadata_path( self ) -> Path:
		return self._metadata_path

	@property
	def schema_path( self ) -> Path:
		return self._schema_path

	# properties for content access

	@property
	def activity_map( self ) -> Dict[int, Activity]:
		return self._activities

	@property
	def activities( self ) -> List[Activity]:
		return list( self._activities.values() )

	@property
	def activity_keys( self ) -> List[int]:
		return sorted( list( self._activities.keys() ) )

	@property
	def resource_map( self ) -> Dict[int, Resource]:
		return self._resources

	@property
	def resources( self ) -> List[Resource]:
		return list( self._resources.values() )

	@property
	def resource_keys( self ) -> List[int]:
		return sorted( list( self._resources.keys() ) )

	# ---- DB Operations --------------------------------------------------------

	# noinspection PyMethodMayBeStatic
	def _next_id( self, d: Dict ) -> int:
		key_range = range( 1, max( d.keys() ) + 2 ) if d.keys() else [1]
		return set( key_range ).difference( set( d.keys() ) ).pop()

	# insert/upsert activities

	def insert( self, *activities ) -> Union[int, List[int]]:
		ids = []
		for a in activities:
			a.id = self._next_id( self._activities )
			self._activities[a.id] = a
			ids.append( a.id )
		return ids[0] if len( ids ) == 1 else ids

	def insert_activity( self, activity: Activity ) -> int:
		activity.id = self._next_id( self._activities )
		self._activities[activity.id] = activity
		return activity.id

	def insert_activities( self, activities: List[Activity] ) -> List[int]:
		return [ self.insert_activity( a ) for a in activities ]

	def upsert_activity( self, activity: Activity ) -> int:
		if existing := self.get_activity_by_uids( activity.uids ):
			self._activities[existing.id] = activity
			activity.id = existing.id
			return activity.id
		else:
			self.insert_activity( activity )

	# insert resources

	def insert_resource( self, resource: Resource ) -> int:
		resource.id = self._next_id( self._resources )
		self._resources[resource.id] = resource
		return resource.id

	def insert_resources( self, resources: List[Resource] ) -> List[int]:
		return [ self.insert_resource( r ) for r in resources ]

	def upsert_resource( self, resource: Resource ) -> int:
		if existing := self.get_resource_by_uid_path( resource.uid, resource.path ):
			self.resource_map[existing.id] = resource
			return existing.id
		else:
			return self.insert_resource( resource )

	# remove items

	def remove_activity( self, a: Activity ) -> None:
		del self.activity_map[a.id]

	def remove_activities( self, activities: List[Activity], auto_commit: bool = False ) -> None:
		[self.remove_activity( a ) for a in activities]
		self.commit( auto_commit )

	# -----

	@property
	def summaries( self ) -> List[Resource]:
		"""
		Returns all resource of type summary.
		"""
		return [r for r in self.resources if (rt := cast( ResourceType, Registry.resource_types.get( r.type ) )) and rt.summary]

	@property
	def uids( self, classifier: str = None ) -> List[str]:
		"""
		Returns a list of all known uids.
		Optionally restrict the list to contain only resources with the given classifier.
		"""
		if classifier:
			return list( set( [r.uid for r in self.resources if r.classifier == classifier] ) )
		else:
			return list( set( [r.uid for r in self.resources] ) )

	# def contains( self, id: Optional[int] = None, raw_id: Optional[int] = None, classifier: Optional[str] = None, uid: Optional[str] = None, filters: Union[List[str], List[Filter], str, Filter] = None ) -> bool:
	# 	filters = parse_filters( filters ) if filters else self._create_filter( id, raw_id, classifier, uid )
	# 	for a in self.activities.all():
	# 		if all( [f( a ) for f in filters] ):
	# 			return True
	# 	return False

	def contains_activity( self, uid: str ) -> bool:
		return any( uid in a.uids for a in self.activities )

	def contains_resource( self, uid: str, path: str ) -> bool:
		return any( r.uid == uid and r.path == path for r in self.resources )

	# def get( self, id: Optional[int] = None, raw_id: Optional[int] = None, classifier: Optional[str] = None, uid: Optional[str] = None, filters: Union[List[str], List[Filter], str, Filter] = None ) -> Optional[Activity]:
	# 	filters = parse_filters( filters ) if filters else self._create_filter( id, raw_id, classifier, uid )
	# 	for a in self.activities.all():
	# 		if all( [f( a ) for f in filters] ):
	# 			return cast( Activity, a )
	# 	return None

	def get_by_id( self, id: int ) -> Optional[Activity]:
		"""
		Returns the activity with the provided id.
		"""
		return self.activity_map.get( id )

	def get_by_uid( self, uid: str, include_resources: bool = False ) -> Optional[Activity]:
		"""
		Returns the activity with the provided uid contained in its uids list.
		"""
		return next( (a for a in self.activities if uid in a.uids), None )

	def get_activity_by_uids( self, uids: List[str] ):
		return next( (a for a in self.activities if any( uid in a.uids for uid in uids ) ), None )

	def get_resource( self, id: int ) -> Optional[Resource]:
		return self._resources.get( id )

	def get_resources_by_uid( self, uid ) -> List[Resource]:
		return [r for r in self.resources if r.uid == uid]

	def get_resources_by_uids( self, uids: List[str] ):
		# regular_list = [[1, 2, 3, 4], [5, 6, 7], [8, 9]]
		# flat_list = [item for sublist in regular_list for item in sublist]
		return list( chain( *[r for r in [self.get_resources_by_uid( uid ) for uid in uids]] ) ) # todo: revise flatten list!

	def get_resource_by_uid_path( self, uid: str, path: str ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.uid == uid and r.path == path), None )

	def get_resource_of_type( self, uids: List[str], type: str ) -> Optional[Resource]:
		return next( iter( [ r for r in self.find_all_resources( uids ) if r.type == type] ), None )

	def get_summary( self, uid ) -> Resource:
		return next( iter( self.find_summaries( uid ) ), None )

	# several find methods to make life easier

	# find activities

	def find( self, filters: List[str] = None ) -> List[Activity]:
		all_activities = self.activities
		for r in parse_rules( *filters ):
			# all_activities = filter( r.evaluate, all_activities )
			all_activities = r.filter( all_activities )
		return list( all_activities )

	def find_by_classifier( self, classifier: str ) -> List[Activity]:
		"""
		Finds all activities, which have a certain classifier (originate from a certain service, i.e. polar).
		"""
		return [a for a in self.activities if any( uid.startswith( classifier ) for uid in a.uids ) ]

	def find_first( self, classifier: Optional[str] = None ) -> Optional[Activity]:
		"""
		Finds the oldest activity. Optionally restricts itself to activities with the given classifier.
		"""
		activities = self.find_by_classifier( classifier ) if classifier else self.activities
		return min( activities, key=lambda a: a.time )

	def find_last( self, classifier: Optional[str] = None ) -> Optional[Activity]:
		"""
		Finds the newest activity. Optionally restricts itself to activities with the given classifier.
		"""
		activities = self.find_by_classifier( classifier ) if classifier else self.activities
		return max( activities, key=lambda a: a.time )

	# find resources

	def find_resources( self, uid: str, path: Optional[str] = None ) -> List[Resource]:
		"""
		Finds resources having the given uid and optionally the given path.
		"""
		resources = [ r for r in self.resources if r.uid == uid ]
		if path:
			resources = [ r for r in resources if r.path == path ]
		return resources

	def find_resources_of_type( self, activity_type: str, resources: Optional[List[Resource]] = None ) -> List[Resource]:
		"""
		Finds all resources of the given type. If resources list is provided restricts itself to that list or uses
		all resources otherwise.
		"""
		resources = self.resources if resources is None else resources
		return [r for r in resources if r.type == activity_type ]

	def find_resources_for( self, activity: Activity ) -> List[Resource]:
		"""
		Finds all resources related to a given activity.
		"""
		resources = [r for r in self.resources if r.uid in [uid.clspath for uid in activity.as_uids]]
		# simplifiy this?
		return [r for r in resources if r.uidpath in activity.uids or r.uid in activity.uids]

	def find_all_resources( self, uids: List[str] ) -> List[Resource]:
		"""
		Finds all resources having an uid contained in the provided list of uids.
		"""
		return [r for r in self.resources if r.uid in uids]

	def find_recordings( self, resources: Optional[List[Resource]] = None ) -> List[Resource]:
		"""
		Finds all recording resources, restricts itself to the provided resource list if given.
		"""
		resources = self.resources if resources is None else resources
		return [r for r in resources if (rt := Registry.resource_types.get( r.type )) and rt.recording ]

	def find_summaries( self, uid: str ) -> List[Resource]:
		"""
		Finds all summary resources having the provided uid.
		"""
		return [r for r in self.find_resources( uid ) if (rt := Registry.resource_types.get( r.type )) and rt.summary ]

	def find_all_summaries( self, uids: List[str] ) -> List[Resource]:
		"""
		Finds all summary resources having an uid contained in the provided list.
		"""
		return [r for r in self.find_all_resources( uids ) if (rt := Registry.resource_types.get( r.type ) ) and rt.summary]

	def find_all_resources_for( self, activities: Union[Activity, List[Activity]] ) -> List[Resource]:
		activities = [activities] if type( activities ) is Activity else activities
		return self.find_all_resources( list( chain( *[a.uids for a in activities] ) ) )

# ---- DB Operations ----

def backup_db( ctx: ApplicationContext ) -> None:
	source = ctx.db_path
	target = Path( ctx.backup_path, f"{datetime.now( timezone.utc ).strftime( '%Y%m%d_%H%M%S' )}" )
	copytree( source, target, ignore=lambda root, content: [c for c in content if c not in DB_FILES.keys()] )
	ctx.console.print( f'created database backup in {target}' )

def restore_db( ctx: ApplicationContext ) -> None:
	target = ctx.db_path
	try:
		source = sorted( list( ctx.backup_path.glob( '[0-9]*_[0-9]*' ) ), key=lambda p: p.name )[-1]
		if ctx.force or confirm( f'Restore database from {source}? The current state will be overwritten.' ):
			copytree( source, target, ignore=lambda root, content: [c for c in content if c not in DB_FILES.keys()], dirs_exist_ok=True )
			log.info( f"database restored from {source}" )
	except RuntimeError:
		log.error( 'failed to restore backup', exc_info=True )
		ctx.console.print( f'no backups found in {ctx.backup_path}' )

def status_db( ctx: ApplicationContext ) -> None:
	table = RichTable( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'activities', pp( len( ctx.db.activity_map ) ) )
	for s in Registry.service_names():
		table.add_row( f'activities ({s})', pp( len( list( ctx.db.find_by_classifier( s ) ) ) ) )

	table.add_row( 'resources', pp( len( ctx.db.resource_map ) ) )

	ctx.console.print( table )

def maintain_db( ctx: ApplicationContext, maintenance: str, **kwargs ) -> None:
	if not maintenance:
		[ctx.console.print( f ) for f in migrate_db_functions( ctx )]
	else:
		backup_db( ctx )
		migrate_db( ctx, maintenance, **kwargs )

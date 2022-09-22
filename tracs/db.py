
from datetime import datetime
from datetime import timezone
from importlib.resources import path as resource_path
from shutil import copy
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from click import confirm
from logging import getLogger
from pathlib import Path
from rich import box
from rich.pretty import pretty_repr as pp
from rich.table import Table as RichTable
from typing import Mapping

from tinydb import TinyDB
from tinydb import Query
from tinydb.operations import delete
from tinydb.operations import set
from tinydb.storages import JSONStorage
from tinydb.table import Document
from tinydb.table import Table

from .activity import Activity
from .activity import Resource
from .activity import ResourceGroup
from .config import CLASSIFIER
from .config import KEY_GROUPS
from .config import console
from .config import APPNAME
from .config import TABLE_NAME_DEFAULT
from .config import KEY_SERVICE
from .config import KEY_VERSION
from .db_storage import DataClassStorage
from .filters import Filter
from .filters import classifier as classifier_filter
from .filters import false as false_filter
from .filters import parse_filters
from .filters import raw_id as raw_id_filter
from .filters import uid as uid_filter
from .plugins import Registry

log = getLogger( __name__ )

ACTIVITIES_NAME = 'activities.json'
METADATA_NAME = 'metadata.json'
RESOURCES_NAME = 'resources.json'
SCHEMA_NAME = 'schema.json'

class ActivityDb:

	def __init__( self, path: Path = None, activities_name: str = None, metadata_name: str = None, resources_name: str = None, schema_name: str = None, pretend: bool=False, cache: bool=False, passthrough=False ):
		"""
		Creates an activity db, consisting of tiny db instances (meta + activities + resources + schema).

		:param path: directory containing dbs
		:param pretend: pretend mode - allows write operations, but does not persist anything to disk
		:param cache: enable db caching
		:param passthrough: plain mode, opens activity db without middleware
		"""

		# names
		self._activities_name = activities_name if activities_name else ACTIVITIES_NAME
		self._metadata_name = metadata_name if metadata_name else METADATA_NAME
		self._resources_name = resources_name if resources_name else RESOURCES_NAME
		self._schema_name = schema_name if schema_name else SCHEMA_NAME

		with resource_path( __package__, '__init__.py' ) as pkg_path:
			self._db_resource_path = Path( pkg_path.parent, 'db' )
			if path:
				self._activities_path = Path( path, self._activities_name )
				self._metadata_path = Path( path, self._metadata_name )
				self._resources_path = Path( path, self._resources_name )
				self._schema_path = Path( path, self._schema_name )

				path.mkdir( parents=True, exist_ok=True )

				if not self._schema_path.exists():
					copy( Path( self._db_resource_path, SCHEMA_NAME ), self._schema_path )
				if not self._activities_path.exists():
					copy( Path( self._db_resource_path, ACTIVITIES_NAME ), self._activities_path )
				if not self._metadata_path.exists():
					copy( Path( self._db_resource_path, METADATA_NAME ), self._metadata_path )
				if not self._resources_path.exists():
					copy( Path( self._db_resource_path, RESOURCES_NAME ), self._resources_path )
			else:
				self._activities_path = Path( self._db_resource_path, ACTIVITIES_NAME )
				self._resources_path = Path( self._db_resource_path, RESOURCES_NAME )
				self._metadata_path = Path(  self._db_resource_path, METADATA_NAME )
				self._schema_path = Path( self._db_resource_path, SCHEMA_NAME )

				pretend = True # turn on in-memory mode when path is not provided

		# init schema db
		self._default_schema: TinyDB = TinyDB( storage=JSONStorage, path=Path( self._db_resource_path, SCHEMA_NAME ), access_mode='r' )
		self._default_schema_version = self._default_schema.all()[0][KEY_VERSION]
		self._schema: TinyDB = TinyDB( storage=JSONStorage, path=self._schema_path, access_mode='r' )
		self._schema_version = self._schema.all()[0][KEY_VERSION]

		# init activities db
		self._db: TinyDB = TinyDB( storage=DataClassStorage, path=self._activities_path, use_memory_storage=pretend, use_cache=cache, passthrough=True )
		self._storage: DataClassStorage = cast( DataClassStorage, self._db.storage )
		self._activities = self.db.table( TABLE_NAME_DEFAULT )
		self._activities.document_class = Activity

		# init resources db
		self._resources_db: TinyDB = TinyDB( storage=DataClassStorage, path=self._resources_path, use_memory_storage=pretend, use_cache=cache, passthrough=True, use_serializers=False )
		self._resources = self._resources_db.table( TABLE_NAME_DEFAULT )
		self._resources.document_class = Resource

		# init resources db
		self._metadata_db: TinyDB = TinyDB( storage=JSONStorage, path=self._metadata_path, access_mode='r' )
		self._metadata = self._metadata_db.table( TABLE_NAME_DEFAULT )

	# ---- DB Properties --------------------------------------------------------

	@property
	def db( self ) -> TinyDB:
		return self._db

	@property
	def activities_db( self ) -> TinyDB:
		return self._db

	@property
	def resources_db( self ) -> TinyDB:
		return self._resources_db

	@property
	def metadata_db( self ) -> TinyDB:
		return self._metadata_db

	@property
	def schema_db( self ) -> TinyDB:
		return self._schema

	@property
	def default_schema_db( self ) -> TinyDB:
		return self._default_schema

	@property
	def metadata( self ) -> Table:
		return self._metadata

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
	def storage( self ) -> DataClassStorage:
		return cast( DataClassStorage, self._db.storage )

	@property
	def activities( self ) -> Table:
		return self._activities

	@property
	def resources( self ) -> Table:
		return self._resources

	@property
	def schema( self ) -> int:
		return self._schema_version

	@property
	def default_schema( self ) -> int:
		return self._default_schema_version

	# ---- DB Operations --------------------------------------------------------

	def insert( self, docs: Union[Activity, List[Activity]] ) -> Union[int, List[int]]:
		docs = [docs] if isinstance( docs, Activity ) else docs

		doc_ids = self.activities.insert_multiple( docs )
		for doc, doc_id in zip( docs, doc_ids ):
			doc.doc_id = doc_id

		return doc_ids if len( doc_ids ) > 1 else doc_ids[0]

	def insert_resource( self, r: Resource ) -> int:
		return self.resources.insert( r )

	def update( self, a: Activity ) -> None:
		self.activities.update( dict( a ), doc_ids=[a.doc_id] )

	def update_resource( self, r: Resource ) -> None:
		self.resources.update( dict( r ), doc_ids=[r.doc_id] )

	def remove( self, a: Activity ) -> None:
		self._activities.remove( doc_ids=[a.doc_id] )

	def remove_field( self, a: Activity, field: str ) -> None:
		if field.startswith( '_' ):
			self._activities.update( set( field, None ), doc_ids=[a.doc_id] )
		else:
			self._activities.update( delete( field ),  doc_ids=[a.doc_id] )

	# -----

	def all( self ) -> List[Activity]:
		"""
		Retrieves all activities stored in the internal db.

		:return: list containing all activities
		"""
		return cast( List[Activity], self.activities.all() )

	def contains( self, id: Optional[int] = None, raw_id: Optional[int] = None, classifier: Optional[str] = None, uid: Optional[str] = None, filters: Union[List[str], List[Filter], str, Filter] = None ) -> bool:
		filters = parse_filters( filters ) if filters else self._create_filter( id, raw_id, classifier, uid )
		for a in self.activities.all():
			if all( [ f( a ) for f in filters ] ):
				return True
		return False

	def get( self, id: Optional[int] = None, raw_id: Optional[int] = None, classifier: Optional[str] = None, uid: Optional[str] = None, filters: Union[List[str], List[Filter], str, Filter] = None ) -> Optional[Activity]:
		filters = parse_filters( filters ) if filters else self._create_filter( id, raw_id, classifier, uid )
		for a in self.activities.all():
			if all( [ f( a ) for f in filters ] ):
				return cast( Activity, a )
		return None

	def get_by_uid( self, uid: str, include_resources: bool = False ) -> Optional[Activity]:
		activity = cast( Activity, next( a for a in self.activities.all() if uid_filter( uid )( a ) ) )
		if activity and include_resources:
			activity.resources = self.get_resources_by_uid( uid )
		return  activity

	def get_resources_by_uid( self, uid ) -> List[Resource]:
		return cast( List[Resource], self.resources.search( Query()['uid'] == uid ) or [] )

	def _create_filter( self, id: Optional[int] = None, raw_id: Optional[int] = None, classifier: Optional[str] = None, uid: Optional[str] = None ) -> List[Filter]:
		if id and id > 0:
			return [ Filter( 'id', id ) ]
		elif raw_id and raw_id > 0:
			return [ uid_filter( f'{classifier}:{raw_id}' ) ] if classifier else [ raw_id_filter( raw_id ) ]
		elif uid:
			return [ uid_filter( uid ) ]
		else:
			return [ false_filter() ]

	# ----

	def find( self, filters: Union[List[str], List[Filter], str, Filter] = None ) -> [Activity]:
		parsed_filters = parse_filters( filters or [] )
		all_activities = self.activities.all()
		for f in parsed_filters:
			all_activities = filter( f, all_activities )
		return all_activities

	def find_by_classifier( self, classifier: str ) -> [Activity]:
		return self.find( classifier_filter( classifier ) )

	def find_ids( self, filters: Union[List[str], List[Filter], str, Filter] = None ) -> [int]:
		return [a.doc_id for a in self.find( filters )]

	def find_by_id( self, id: int = 0 ) -> Optional[Activity]:
		a = self.get( id = id ) if id > 0 else None # try get by id
		a = self.get( raw_id = id ) if not a else a # try get by raw id
		return a

	def find_last( self, service_name: Optional[str] ) -> Optional[Activity]:
		if service_name:
			_all = self.find( [f'{KEY_SERVICE}:{service_name}'] )
		else:
			_all = self.find( [] )

		_all = self.filter( _all, [Query().time.exists()] )
		return max( _all, key=lambda x: x.get( 'time' ) ) if len( _all ) > 0 else None

	def find_resource( self, uid: str, path: str = None ) -> Optional[Activity]:
		return self.resources.get( ( Query()['uid'] == uid ) & ( Query()['path'] == path ) )

	def find_resources( self, uid: str, path: str = None ) -> List[Resource]:
		if path:
			resources = self.resources.search( ( Query()['uid'] == uid ) & ( Query()['path'] == path ) )
		else:
			resources = self.resources.search( Query()['uid'] == uid )

		return cast( List[Resource], resources )

	def find_resource_group( self, uid: str, path: str = None ) -> ResourceGroup:
		return ResourceGroup( resources=self.find_resources( uid, path ) )

	def contains_resource( self, uid: str, path: str ) -> bool:
		return self.resources.contains( ( Query()['uid'] == uid ) & ( Query()['path'] == path ) )

	# noinspection PyMethodMayBeStatic
	def filter( self, activities: [Activity], queries: [Query] ) -> [Activity]:
		for q in queries or []:
			activities = list( filter( q, activities or [] ) )
		return activities

	def query( self, queries: [Query] ) -> [Activity]:
		if len( queries ) == 0:
			query = Query().noop()
		else:
			query = queries[0]
			for q in queries[1:]:
				query = query & q

		return self._activities.search( query )

# ---- DB Factory ---

def document_cls( doc: Union[Dict, Document], doc_id: int ) -> Type:
	if classifier := doc.get( CLASSIFIER ):
		if classifier == 'group': # ActvityGroup is registered with 'groups' todo: improve!
			classifier = KEY_GROUPS
		if classifier in Registry.document_classes:
			return Registry.document_classes.get( classifier )
	elif groups := doc.get( KEY_GROUPS ):
		if 'ids' in groups.keys() or 'uids' in groups.keys():
			return Registry.document_classes.get( KEY_GROUPS )

	return Document

def document_factory( doc: Union[Dict, Document], doc_id: int ) -> Document:
	return document_cls( doc, doc_id )( doc, doc_id )

def create_metadb( path: Path = None, use_memory_storage: bool = False, cache: bool = False ) -> TinyDB:
	return TinyDB( storage=DataClassStorage, path=path, use_memory_storage=use_memory_storage, cache=cache, passthrough=True )

def create_db( path: Path = None, use_memory_storage: bool = False, cache: bool = False, passthrough = False ) -> TinyDB:
	return TinyDB( storage=DataClassStorage, path=path, use_memory_storage=use_memory_storage, cache=cache, passthrough=passthrough )

# ---- DB Operations ----

def backup_db( db_file: Path, backup_dir: Path ) -> None:
	backup_dir.mkdir( parents=True, exist_ok=True )
	backup_file = Path( backup_dir, f"{APPNAME}.db.{datetime.now( timezone.utc ).strftime( '%Y%m%d_%H%M%S' )}.json" )
	copy( db_file, backup_file )
	log.info( f"created database backup in {backup_file}" )

def restore_db( db: TinyDB, db_file: Path, backup_dir: Path, force: bool ) -> None:
	backup_dir.mkdir( parents=True, exist_ok=True )
	glob_pattern = f'{APPNAME}.db.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].json'
	files = list( backup_dir.glob( glob_pattern ) )
	if len( files ) > 0:
		files.sort( reverse=True )
		log.info( f'restoring backup from {files[0].name}' )
		if not force:
			if not confirm( f'Restore database from {files[0].name}? The current state will be overwritten!' ):
				log.info( f"database restore from {files[0].name} aborted ..." )
				return

		db.close()
		copy( files[0], db_file )
		log.info( f"database restored from {files[0].name}" )
	else:
		log.info( f"no backups found in {backup_dir}" )

def status_db( db: ActivityDb, services: Mapping ) -> None:
	table = RichTable( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'activities in database:', pp( len( db.all() ) ) )
	table.add_row( 'activity groups:', pp( len( db.all( True, False, False ) ) ) )
	table.add_row( 'activities being part of a group:', pp( len( db.all( False, True, False ) ) ) )
	table.add_row( 'ungrouped activities:', pp( len( db.all( False, False, True ) ) ) )
	for s in services.values():
		activities = list( db.find( f'service:{s.name}', False, True, True ) )
		table.add_row( f'activities from {s.display_name}:', pp( len( activities ) ) )

	table.add_row( 'activities without name:', pp( db.activities.count( Query().name == '' ) ) )

	console.print( table )


from collections import OrderedDict
from datetime import datetime
from datetime import timezone
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
from rich.table import Table
from typing import Mapping

from tinydb import Storage
from tinydb import TinyDB
from tinydb import Query
from tinydb.middlewares import CachingMiddleware
from tinydb.operations import delete
from tinydb.operations import set
from tinydb.storages import MemoryStorage
from tinydb.table import Document
from tinydb.table import Table

from .activity import Activity
from .config import CLASSIFIER
from .config import KEY_GROUPS
from .config import console
from .config import APPNAME
from .config import TABLE_NAME_ACTIVITIES
from .config import TABLE_NAME_DEFAULT
from .config import KEY_SERVICE
from .config import KEY_VERSION
from .db_middleware import DataClassMiddleware
from .db_storage import OrJSONStorage
from .filters import Filter
from .filters import groups
from .filters import grouped
from .filters import ungrouped
from .filters import parse_filters
from .plugins import Registry
from .queries import is_group
from .queries import is_grouped
from .queries import is_ungrouped

log = getLogger( __name__ )

DB_VERSION = 12

class ActivityDb:

	def __init__( self, db: TinyDB=None, path: Path=None, pretend: bool=False, cache: bool=False ):

		# use provided db instead of creating a new one -> mainly for test purposes
		self._db: TinyDB = create_db( db, path, pretend=pretend, cache=cache )
		self._path: Path = path # save db path for later use
		self._storage: Storage = self._db.storage

		# configure default table, only contains db version number
		self._default = self.db.table( TABLE_NAME_DEFAULT )
		if not self._default.search( Query().version.exists() ):
			self._default.insert( { KEY_VERSION: DB_VERSION } )
		self._default.document_class = Document

		# configure activities table
		self._activities = self.db.table( TABLE_NAME_ACTIVITIES )
		self._activities.document_class = document_factory

		if self.middleware:
			self.middleware.transmap[TABLE_NAME_ACTIVITIES] = document_cls

	# ---- DB Properties --------------------------------------------------------

	@property
	def db( self ) -> TinyDB:
		return self._db

	@property
	def path( self ) -> Path:
		return self._path

	@property
	def middleware( self ) -> Optional[DataClassMiddleware]:
		if type( self._storage ) is CachingMiddleware:
			return cast( CachingMiddleware, self._storage ).storage
		elif type( self._storage ) is DataClassMiddleware:
			return cast( DataClassMiddleware, self._storage )
		else:
			return None

	@property
	def storage( self ) -> Union[MemoryStorage, OrJSONStorage]:
		return self.middleware.storage if self.middleware else None

	@property
	def default( self ) -> Table:
		return self._default

	@property
	def activities( self ) -> Table:
		return self._activities

	# ---- DB Operations --------------------------------------------------------

	def insert( self, doc: Mapping ) -> int:
		if isinstance( doc, Document ):
			doc_id = self.activities.insert( dict( doc ) )
			if doc.doc_id == 0:
				doc.doc_id = doc_id
		else:
			doc_id = self.activities.insert( doc )

		return doc_id

	def update( self, a: Activity ) -> None:
		self.activities.update( dict( a ), doc_ids=[a.doc_id] )

	def remove( self, a: Activity ) -> None:
		self._activities.remove( doc_ids=[a.doc_id] )

	def remove_field( self, a: Activity, field: str ) -> None:
		if field.startswith( '_' ):
			self._activities.update( set( field, None ), doc_ids=[a.doc_id] )
		else:
			self._activities.update( delete( field ),  doc_ids=[a.doc_id] )

	# -----

	def all_exclude( self, group: bool = True, grouped: bool = True, ungrouped: bool = True ) -> List[Activity]:
		activities = self.activities.all() or []
		activities = list( filter( is_group(), activities ) ) if group else activities
		activities = list( filter( is_grouped(), activities ) ) if grouped else activities
		activities = list( filter( is_ungrouped(), activities ) ) if ungrouped else activities
		return activities

	def all( self, include_groups: bool = True, include_grouped: bool = False, include_ungrouped = True ) -> [Activity]:
		"""
		Retrieves all activities stored in the internal db.

		:param include_groups: when True includes activity groups (this is the default)
		:param include_grouped: when True includes grouped activities (default is False)
		:param include_ungrouped: when True includes ungrouped activities (default is False)
		:return: list containing all activities
		"""
		od = OrderedDict()
		for a in self.activities.search( groups() ) if include_groups else []:
			od[a.doc_id] = a
		for a in self.activities.search( grouped() ) if include_grouped else []:
			od[a.doc_id] = a
		for a in self.activities.search( ungrouped() ) if include_ungrouped else []:
			od[a.doc_id] = a
		return list( od.values() )

		#return self.activities.search( f_all( include_groups, include_grouped, include_ungrouped ) )

	def contains( self, id: Optional[int] = None, raw_id: Optional[int] = None, service_name: Optional[str] = None ) -> bool:
		"""
		Checks if the db contains an activitiy with the provided id.

		:param id: id of the activity to be checked
		:param raw_id: raw id of the activity to be checked
		:param service_name: if provided checks for external activities
		:return: true, if the activity can be found
		"""
		if id and id > 0:
			return self.activities.contains( Filter( 'id', id ) )
		elif raw_id and raw_id > 0:
			if service_name:
				return self.activities.contains( Filter( 'uid', f'{service_name}:{raw_id}' ) )
			else:
				return self.activities.contains( Filter( 'raw_id', raw_id ) )
		else:
			return False

	# ----

	def get( self, doc_id: Optional[int] = None, raw_id: Optional[int] = None, service_name: Optional[str] = None ) -> Optional[Activity]:
		if doc_id and doc_id > 0:
			return self.activities.get( doc_id=doc_id )
		elif raw_id and raw_id > 0:
			if service_name:
				return self.activities.get( Filter( 'uid', f'{service_name}:{raw_id}' ) )
			else:
				return self.activities.get( Filter( 'raw_id', raw_id ) )
		else:
			return None

	def find( self, filters: Union[List[str], str] = None, include_groups: bool = True, include_grouped: bool = False, include_ungrouped = True ) -> [Activity]:
		filters = [filters] if type( filters ) is str else filters
		parsed_filters = parse_filters( filters or [] )
		all_activities = self.all( include_groups, include_grouped, include_ungrouped )
		for f in parsed_filters:
			all_activities = filter( f, all_activities )
		return all_activities

	def find_ids( self, filters: Union[List[str], str] = None, include_groups: bool = True, include_grouped: bool = False, include_ungrouped = True ) -> [int]:
		return [a.doc_id for a in self.find( filters, include_groups, include_grouped, include_ungrouped )]

	def find_by_id( self, id: int = 0 ) -> Optional[Activity]:
		a = None
		if id > 0:
			a = self.get( doc_id=id )
		if not a:
			a = self.get( raw_id=id )
		return a

	def find_last( self, service_name: Optional[str] ) -> Optional[Activity]:
		if service_name:
			_all = self.find( [f'{KEY_SERVICE}:{service_name}'], False, True, True )
		else:
			_all = self.find( [], True, False, True )

		_all = self.filter( _all, [Query().time.exists()] )
		return max( _all, key=lambda x: x.get( 'time' ) ) if len( _all ) > 0 else None

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

def create_db( db: TinyDB = None, path: Path = None, pretend: bool = False, cache: bool = False ) -> TinyDB:
	if db is not None:
		log.debug( 'create db: using provided database, ignoring arguments' )
		return db

	use_memory_storage = pretend # pretend results in inmemory db created

	if path:
		if cache:
			db = TinyDB( storage=CachingMiddleware( DataClassMiddleware( OrJSONStorage ) ), path=path, use_memory_storage=use_memory_storage )
		else:
			db = TinyDB( storage=DataClassMiddleware( OrJSONStorage ), path=path, use_memory_storage=use_memory_storage )
	else:
		db = TinyDB( storage=DataClassMiddleware( MemoryStorage ) ) # if path is not provided, memory storage is implicit

	return db

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
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'activities in database:', pp( len( db.all() ) ) )
	for s in services.values():
		table.add_row( f'activities from {s.display_name}:', pp( len( db.all( True, True, True ) ) ) )

	table.add_row( 'activities without name:', pp( db.activities.count( Query().name == '' ) ) )

	console.print( table )


from __future__ import annotations

from itertools import chain
from logging import getLogger
from typing import ClassVar, Dict, Iterable, List, Mapping, Optional

from attrs import define, field
from click import Tuple
from fs.base import FS
from fs.wrap import read_only
from more_itertools import first_true, unique
from orjson import dumps
from rich import box
from rich.pretty import pretty_repr as pp
from rich.table import Table as RichTable
from rule_engine import Rule

from tracs.activity import Activities, Activity
from tracs.constants import *
from tracs.fsio import load_activities, load_schema, write_activities
from tracs.migrate import migrate_db, migrate_db_functions
from tracs.protocols import ApplicationContext
from tracs.resources import Resource, Resources
from tracs.uid import UID
from tracs.utils import ResolvingOSFS

log = getLogger( __name__ )

DB_FILES = {
	ACTIVITIES_NAME: dumps( [] ),
	GROUPS_NAME: dumps( [] ),
	MULTIPARTS_NAME: dumps( [] ),
	SCHEMA_NAME: dumps( { "version": SCHEMA_VERSION } )
}

@define
class ActivityDb:

	summary_types: ClassVar[List[str]] = []
	recording_types: ClassVar[List[str]] = []

	fs: FS = field( default=None )

	path: str = field( default=None, kw_only=True )
	read_only: bool = field( default=False, kw_only=True )
	schema: int = field( default=SCHEMA_VERSION, kw_only=True )
	activities: Activities = field( default=None, kw_only=True )

	def __attrs_post_init__( self ):
		# initialize db file system(s)
		self._init_db()

		# load content from disk
		self._load_db()

	def _init_db( self ):
		# create OSFS if path is provided
		if self.path and not self.fs:
			self.fs = ResolvingOSFS( self.path )

		# init FS if not yet done
		for file, content in DB_FILES.items():
			if not self.fs.exists( f'/{file}' ):
				self.fs.writebytes( f'/{file}', content )

		# create read-only FS if needed
		if self.read_only:
			self.fs = read_only( self.fs )

		log.debug( f'initializing db file system in {self.fs}' )
		log.debug( f'expected db schema version is {SCHEMA_VERSION}' )

	def _load_db( self ):
		self.schema = load_schema( self.fs ).version
		self.activities = load_activities( self.fs )

	@staticmethod
	def register_summary_types( *types: str ):
		[ ActivityDb.summary_types.append( t ) for t in types ]

	@staticmethod
	def register_recording_types( *types: str ):
		[ ActivityDb.recording_types.append( t ) for t in types ]

	def save( self ):
		write_activities( self.activities, self.fs )

	# properties for content access

	@property
	def activity_map( self ) -> Mapping[int, Activity]:
		return self.activities.id_map()

	@property
	def activity_keys( self ) -> List[int]:
		return sorted( list( self.activities.ids() ) )

	@property
	def activity_ids( self ) -> List[int]:
		return sorted( list( self.activities.id_keys() ) )

	@property
	def resources( self ) -> Resources:
		return Resources( lst = [r for a in self.activities for r in a.resources] )

	# ---- DB Operations --------------------------------------------------------

	# noinspection PyMethodMayBeStatic
	def _next_id( self, d: Dict ) -> int:
		key_range = range( 1, max( d.keys() ) + 2 ) if d.keys() else [1]
		return set( key_range ).difference( set( d.keys() ) ).pop()

	# insert/upsert activities

	def insert( self, activity: Activity ) -> int:
		return self.activities.add( activity )

	def insert_all( self, activities: Iterable[Activity] ) -> List[int]:
		return [ self.insert( a ) for a in activities ]

	def upsert( self, activity: Activity ) -> int:
		if existing := self.get_by_uid( activity.uid ):
			if existing.group:
				Activity.group_of( existing, activity, target=existing )
			else:
				Activity.union( activity, target=existing, force=True )
			return existing.id
		else:
			return self.insert( activity )

	def upsert_all( self, activities: Iterable[Activity] ) -> List[int]:
		return [ self.upsert( a ) for a in activities ]

	# def replace_activity( self, new: Activity, old: Activity = None, id: int = None, uid = None ) -> None:
	# 	self._activities.replace( new, old, id, uid )

	# remove items

	def remove_activity( self, a: Activity ) -> None:
		self.activities.remove( a.id )

	def remove_activities( self, activities: List[Activity], auto_commit: bool = False ) -> None:
		[self.remove_activity( a ) for a in activities]
		self.commit( auto_commit )

	# -----

	@property
	def summaries( self ) -> List[Resource]:
		"""
		Returns all resource of type summary.
		:return: all summaries
		"""
		# return [r for r in self.resources if (rt := cast( ResourceType, Registry.instance().resource_types.get( r.type ) )) and rt.summary]
		return [r for r in self.resources if r.type in ActivityDb.summary_types ]

	@property
	def recordings( self ) -> List[Resource]:
		"""
		Returns all resources of type recording.
		:return: all recordings
		"""
		return [r for r in self.resources if r.type in ActivityDb.recording_types]

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

	def contains( self, uid: UID|str ) -> bool:
		if (uid := UID.of( uid )).denotes_activity():
			return self.contains_activity( uid )
		elif uid.denotes_resource():
			return self.contains_resource( uid, None )
		else:
			return False

	def contains_activity( self, uid: UID|str ) -> bool:
		return UID.of( uid ) in self.activities

	def contains_resource( self, uid: UID|str, path: Optional[str] ) -> bool:
#		if isinstance( uid, UID ):
#			uid = UID( uid.classifier, uid.local_id, path or uid.path )
#		else:
#			uid = UID( uid, path=path if path else None )
		# return any( (u == uid or u.base == uid.base) for u in self.activities.iter_resource_uids() )
		uid = UID.of( uid, path )
		return any( u.base == uid.base for u in self.activities.iter_resource_uids() )

	# get methods

	def get( self, id: Optional[int] = None, uid: Optional[str] = None ) -> Optional[Activity|List[Activity]]:
		"""
		Convenience get. Intended to be used with one kwarg.
		"""
		if id:
			return self.get_by_id( id )
		elif uid:
			return self.get_by_uid( uid )
		else:
			return None

	def get_by_id( self, id: int ) -> Optional[Activity]:
		"""Returns the (first and only) activity with the provided id.
		There should never be two activities with the same id.
		:param id: id of the activity
		:return: activity or None if not found
		"""
		# return first_true( self.activities, pred=lambda a: a.id == id )
		return self.activities.get_by_id( id )

	def get_by_uid( self, uid: UID|str ) -> Optional[Activity]:
		"""Returns the activity with the uid equal to the provided uid.

		:param uid: uid of the activity
		:return: activity or None if not found
		"""
		return self.activities.get_by_uid( uid )

	def get_for_uid( self, uid: UID|str ) -> Optional[Activity]:
		"""
		Returns the first activity for the given uid.
		This includes activities with the uid equal to the provided uid as well as activities
		where the uid appears as member (groups and multiparts).
		:param uid:
		:return:
		"""
		return first_true( self.activities, pred=lambda a: uid in [ a.uid, *a.metadata.members ] )

	def get_group_for( self, uid: UID|str ) -> Optional[Activity]:
		"""
		Returns the group where the given uid appears as member.
		This does not include activities with the uid equal to the provided.
		:param uid:
		:return:
		"""
		return first_true( self.activities, pred=lambda a: uid in a.metadata.members )

	def get_resource_by_uid_path( self, uid: UID|str, path: str ) -> Optional[Resource]:
		"""
		Returns the resource with the provided uid and path.
		:param uid:
		:param path:
		:return:
		"""
		return next( (r for r in self.find_resources_by_uid( uid ) if r.path == path), None )

	# several find methods to make life easier

	# find activities

	def find( self, rules: List[Rule] = None ) -> List[Activity]:
		all_activities = self.activities
		for r in rules:
			# all_activities = filter( r.evaluate, all_activities )
			all_activities = r.filter( all_activities )
		return list( all_activities )

	def find_by_id( self, ids: List[int] ) -> List[Activity]:
		"""Returns all activities with ids contained in the provided list of ids

		:param ids: list of ids
		:return: list of activities with ids contained in the provided list of ids
		"""
		return [ a for a in self.activities if a.id in ( ids or [] ) ]

	def find_by_uid( self, uids: List[str] ) -> List[Activity]:
		"""Returns all activities with uids contained in the provided list of uids

		:param uids: list of uids
		:return: list of activities with a uid contained in the provided list of uids
		"""
		return [ a for a in self.activities if a.uid in ( uids or [] ) ]

	def find_for_uid( self, uid: UID|str ) -> List[Activity]:
		"""
		Returns all activities for the given uid.
		This includes activities with the uid equal to the provided uid as well as activities
		where the uid appears as member (groups and multiparts)
		:param uid:
		:return:
		"""
		return [ a for a in self.activities if ( uid in [ a.uid, *a.metadata.members ] ) ] if uid else []

	def find_groups_for( self, uid: UID|str ) -> List[Activity]:
		"""Returns all groups with members with the given uid.

		:param uid: uid of a member
		:return: list of groups with members with uid equal to the provided uid
		"""
		return [a for a in self.activities if uid in a.metadata.members ] if uid else []

	def find_by_classifier( self, classifier: str ) -> List[Activity]:
		"""
		Finds all activities, which have a certain classifier (originate from a certain service, i.e. polar).
		"""
		return [a for a in self.activities if any( uid.startswith( classifier ) for uid in a.iter_uid_heads )]

	def find_first( self, classifier: Optional[str] = None ) -> Optional[Activity]:
		"""
		Finds the oldest activity. Optionally restricts itself to activities with the given classifier.
		"""
		activities = self.find_by_classifier( classifier ) if classifier else self.activities
		return min( activities, key=lambda a: a.starttime )

	def find_last( self, classifier: Optional[str] = None ) -> Optional[Activity]:
		"""
		Finds the newest activity. Optionally restricts itself to activities with the given classifier.
		"""
		activities = self.find_by_classifier( classifier ) if classifier else self.activities
		return max( activities, key=lambda a: a.starttime )

	def find_uids( self, classifier: Optional[str] = None ) -> List[UID]:
		uids = list( unique( chain( *[ a.metadata.members if a.group or a.multipart else [a.uid] for a in self.activities ] ) ) )
		return [ u for u in uids if u.classifier == classifier] if classifier else uids

	# find resources

	# todo: create a universal method, like get from above
	def find_resources( self, uid: str, path: Optional[str] = None ) -> List[Resource]:
		"""
		Finds resources having the given uid and optionally the given path.
		"""
		resources = [ r for r in self.resources if r.uid == uid ]
		if path:
			resources = [ r for r in resources if r.path == path ]
		return resources

	def find_resources_by_uid( self, uid: UID|str ) -> Resources:
		"""
		Returns all resources of the activity with the provided uid.
		:param uid:
		:return:
		"""
		return a.resources if ( a:= self.get_by_uid( uid ) ) else []

	def find_resources_by_uids( self, uids: List[UID|str] ) -> Resources:
		"""
		Returns all resources with the provided uids.
		:param uids:
		:return:
		"""
		return Resources( *chain( *[self.find_resources_by_uid( uid ) for uid in uids] ) )

	def find_resources_of_type( self, *types: str ) -> Resources:
		"""
		Finds all resources of the given type.
		"""
		return Resources( *[r for r in self.activities.iter_resources() if r.type in types] )

	def find_resources_for( self, uid: UID|str ) -> Resources:
		"""
		Finds all resources for a given UID. This included all resources when the activity is part of a group.
		"""
		uid = uid if isinstance( uid, UID ) else UID( uid )
		resources = [r for a in self.find_for_uid( uid ) for r in a.resources if uid in [a.uid.head, r.uid.head if r.uid else None ] ]
		return Resources( *unique( resources, key=lambda r: r.path ) )

	def find_recordings( self, *uids: Optional[UID|str] ) -> Resources:
		"""
		Finds all recording resources. Optinally restricts the result to the provided UIDs.
		"""
		resources = Resources( *chain( *[self.find_resources_for( uid ) for uid in uids] ) ) if uids else self.activities.iter_resources()
		return Resources( *[r for r in resources if r.type in self._recording_types] )

	def find_summaries( self, *uids: Optional[UID|str] ) -> Resources:
		"""
		Finds all summary resources. Optinally restricts the result to the provided UIDs.
		"""
		resources = Resources( *chain( *[self.find_resources_for( uid ) for uid in uids] ) ) if uids else self.activities.iter_resources()
		return Resources( *[r for r in resources if r.type in self._summary_types] )

# ---- DB Operations ----

def status_db( ctx: ApplicationContext ) -> None:
	table = RichTable( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'activities', pp( len( ctx.db.activities ) ) )

	activity_map = {}
	for a in ctx.db.activities:
		if a.uid.classifier not in activity_map.keys():
			activity_map[a.uid.classifier] = 1
		else:
			activity_map[a.uid.classifier] = activity_map[a.uid.classifier] + 1

	for k in sorted( activity_map.keys() ):
		table.add_row( f' - {k}', pp( activity_map[k] ) )
	table.add_row( 'resources', pp( len( ctx.db.resources ) ) )

	ctx.console.print( table )

def maintain_db( ctx: ApplicationContext, maintenance: str, **kwargs ) -> None:
	if not maintenance:
		[ctx.console.print( f ) for f in migrate_db_functions( ctx )]
	else:
		migrate_db( ctx, maintenance, **kwargs )

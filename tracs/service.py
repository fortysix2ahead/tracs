
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import cast
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from dateutil.tz import UTC
from fs.base import FS
from fs.multifs import MultiFS
from fs.osfs import OSFS

from .activity import Activity
from .db import ActivityDb
from .plugin import Plugin
from .resources import Resource
from .config import DEFAULT_DB_DIR
from .config import OVERLAY_DIRNAME
from .config import ApplicationContext
from .config import GlobalConfig as gc
from .config import KEY_LAST_DOWNLOAD
from .config import KEY_LAST_FETCH
from .config import KEY_PLUGINS
from .registry import Registry
from .resources import ResourceType
from .utils import unarg

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( **kwargs )

		# paths + plugin filesystem area
		self._base_path: Path = kwargs.get( 'base_path', Path( DEFAULT_DB_DIR, self.name ) )
		self._overlay_path: Path = kwargs.get( 'overlay_path', Path( self._base_path.parent, OVERLAY_DIRNAME, self.name ) )

		self._fs: MultiFS = MultiFS()
		self._fs.add_fs( 'base', OSFS( str( self._base_path ), create=True ), write=True )
		self._fs.add_fs( 'overlay', OSFS( str( self._overlay_path ), create=True ), write=False )

		self._base_url: str = kwargs.get( 'base_url' )
		self._logged_in: bool = False

		log.debug( f'service instance {self._name} created, with base path = {self._base_path} and overlay_path = {self._overlay_path} ' )

	# properties

	@property
	def logged_in( self ) -> bool:
		return self._logged_in

	@property
	def base_path( self ) -> Path:
		return self._base_path

	@base_path.setter
	def base_path( self, path: Path ) -> None:
		self._base_path = path

	@property
	def overlay_path( self ) -> Path:
		return self._overlay_path

	@overlay_path.setter
	def overlay_path( self, path: Path ) -> None:
		self._overlay_path = path

	@property
	def base_url( self ) -> str:
		return self._base_url

	@property
	def _db( self ) -> ActivityDb:
		return self.ctx.db

	# fs properties

	@property
	def fs( self ) -> FS:
		return self._fs

	@property
	def base_fs( self ) -> FS:
		return self._fs.get_fs( 'base' )

	@property
	def overlay_fs( self ) -> FS:
		return self._fs.get_fs( 'overlay' )

	# some helper class methods

	@classmethod
	def path_for_uid( cls, uid: str ) -> Optional[Path]:
		classifier, local_id = uid.split( ':', 1 )
		if service := cast( cls, Registry.services.get( classifier ) ):
			return Path( service.name, service.path_for_id( local_id, None ) )
		else:
			return None

	@classmethod
	def path_for_resource( cls, resource: Resource ) -> Optional[Path]:
		if service := Registry.services.get( resource.classifier ):
			#return Path( service.path_for_id( raw_id, service.base_path ), resource.path )
			return service.path_for( resource=resource ).resolve()

	@classmethod
	def url_for_uid( cls, uid: str ) -> Optional[str]:
		classifier, local_id = uid.split( ':', 1 )
		if service := Registry.services.get( classifier ):
			return service.url_for( local_id=local_id )
		else:
			return None

	def path_for_id( self, raw_id: int, base_path: Optional[Path] ) -> Path:
		_id = str( raw_id )
		rel_path = Path( _id[0], _id[1], _id[2], _id )
		return Path( base_path, rel_path ) if base_path else rel_path

	def path_for( self, activity: Activity = None, resource: Resource = None, ignore_overlay: bool = True ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.

		:param activity: activity
		:param resource: resource
		:param ignore_overlay:
		:return: path of the activity in the local file system
		"""
		path, overlay_path = None, None
		if activity:
			rel_path = self.path_for_id( activity.raw_id, base_path=None )
			path = Path( self.base_path, rel_path )
			overlay_path = Path( self.overlay_path, rel_path )
		elif resource:
			rel_path = self.path_for_id( resource.local_id, base_path=None )
			path = Path( self.base_path, rel_path, resource.path )
			overlay_path = Path( self.overlay_path, rel_path, resource.path )

		if ignore_overlay:
			return path
		else:
			return overlay_path if overlay_path else path

	def link_for( self, activity: Optional[Activity], resource: Optional[Resource], ext: Optional[str] = None ) -> Optional[Path]:
		ts = activity.time.strftime( '%Y%m%d%H%M%S' )
		path = Path( gc.lib_dir, ts[0:4], ts[4:6], ts[6:8] )
		if resource:
			path = Path( path, f'{ts[8:]}.{self.name}.{resource.type}' )
		elif ext:
			path = Path( path, f'{ts[8:]}.{self.name}.{ext}' )
		return path

	def url_for( self, activity: Optional[Activity] = None, resource: Optional[Resource] = None, local_id: Optional[int] = None ) -> Optional[str]:
		url = None

		if local_id:
			url = self.url_for_id( local_id )
		elif resource and resource.classifier == self.name:
			url = self.url_for_resource_type( resource.local_id, resource.type )
		elif activity:
			try:
				classifier, local_id = activity.uid.split( ':', 1 )
				if classifier == self.name:
					url = self.url_for_id( local_id )
			except KeyError:
				pass

		return url

	@abstractmethod
	def url_for_id( self, local_id: Union[int, str] ) -> str:
		pass

	@abstractmethod
	def url_for_resource_type( self, local_id: Union[int, str], type: str ):
		pass

	# login method

	def login( self ) -> bool:
		pass

	# methods related to fetch()

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		"""
		This method has to be implemented by a service class. It shall fetch information for
		activities from an external service and return a list of summary resources. This way it can be checked
		what activities exist and which identifier they have.

		:param force: flag to signal force execution
		:param pretend: pretend flag, do not persist anything
		:param kwargs: additional parameters
		:return: list of fetched summary resources
		"""
		return []

	def fetch_ids( self ) -> List[int]:
		return [ r.local_id for r in self.fetch( force=False, pretend=False ) ]

	# noinspection PyMethodMayBeStatic
	def filter_fetched( self, resources: List[Resource], *uids, **kwargs ) -> List[Resource]:
		# return [r for r in resources if r.uid in uids] if uids else resources
		return [r for r in resources if r.uid in uids]

	# methods related to download()

	def download( self, summary: Resource, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		"""
		Downloads related resources like GPX recordings based on a provided activity or summary resource.
		TODO: create a method for all services to ease implementation of subclasses.

		:param summary: summary resource
		:param force: flag force
		:param pretend: pretend flag
		:param kwargs: additional parameters
		:return: a list of downloaded resources
		"""
		return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		"""
		Downloads a single resource and returns the content + a status to signal that something has gone wrong.

		:param resource: resource to be downloaded
		:param kwargs: additional parameters
		:return: tuple containing the content + status
		"""
		pass

	def persist_resources( self, *resources: Resource, force: bool, pretend: bool, include_children: bool = True, **kwargs ) -> None:
		for resource in unarg( 'resources', resources, kwargs=kwargs ):
			self.persist_resource( resource, force, pretend, include_children, **kwargs )

	def persist_resource( self, resource: Resource, force: bool, pretend: bool, include_children: bool = True, **kwargs ) -> None:
		path = self.path_for_resource( resource )
		if not force and path and path.exists():
			return

		try:
			if pretend:
				log.info( f'pretending to write resource {resource.uid}?{resource.path}' )
				return

			if resource.content and len( resource.content ) > 0:
				path.parent.mkdir( parents=True, exist_ok=True )
				path.write_bytes( resource.content )
				self.ctx.db.upsert_resource( resource )

			if include_children:
				for r in resource.resources:
					self.persist_resource( r, force, pretend, include_children=False, **kwargs )

		except TypeError:
			log.error( f'error writing resource data for resource {resource.uid}?{resource.path}', exc_info=True )

	def postprocess_resources( self, *resources: Resource, **kwargs ) -> None:
		for resource in unarg( 'resources', resources, kwargs=kwargs ):
			self.postprocess_resource( resource, **kwargs )

	def postprocess_resource( self, resource: Resource = None, **kwargs ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def create_activities( self, resource: Resource, **kwargs ) -> List[Activity]:
		if activity_cls := cast( ResourceType, Registry.resource_types.get( resource.type ) ).activity_cls:
			return [ activity_cls( raw=resource.raw, resources=[resource, *resource.resources] ) ]
		else:
			return []

	def postprocess_activities( self, *activities: Activity, **kwargs ) -> None:
		pass

	def persist_activities( self, *activities: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		for a in activities:
			self.upsert_activity( activity=a, force=force, pretend=pretend, **kwargs )

	def upsert_activity( self, activity: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		if not pretend:
			if self.ctx.db.contains_activity( activity.uid, use_index=False ):  # todo: check if we can use db.upsert here
				# self._ctx.db.update( activity ) # todo: what to do here?
				pass
			else:
				new_activity = Activity().init_from( activity )
				new_activity.uids = [activity.uid]
				new_activity.parts = activity.parts
				self._ctx.db.insert( new_activity )

	def import_activities( self, force: bool = False, pretend: bool = False, **kwargs ):
		skip_fetch = kwargs.get( 'skip_fetch', False ) # not used at the moment
		skip_download = kwargs.get( 'skip_download', False )
		skip_link = kwargs.get( 'skip_link', False ) # not used at the moment
		uids: List[str] = kwargs.get( 'uids', [] )

		self._import_session = ImportSession()

		# fetch

		self.ctx.start( f'fetching activity data from {self.display_name}' )

		# fetch from remote or get items from local storage

		if not skip_fetch:
			summaries = self.fetch( force, pretend, **kwargs )  # fetch 'main' resources for each activity
		else:
			summaries = self.ctx.db.all_summaries()

		self._import_session.all_summaries = summaries

		# if only certain uids were requested: filter out everything else

		if uids:
			summaries = self.filter_fetched( summaries, *uids, **kwargs )

		# process and persist fetched resources

		if not skip_fetch or force:
			self.postprocess_resources( *summaries, **kwargs )  # post process summaries
			self.persist_resources( *summaries, force=force, pretend=pretend, include_children=False, **kwargs ) # persist summaries

			self.ctx.total( len( summaries ) )

			for summary in summaries:
				self.ctx.advance( f'{summary.uid}' )
				activities = self.create_activities( resource=summary, **kwargs )
				self.postprocess_activities( *activities, **kwargs )
				self.persist_activities( *activities, force=force, pretend=pretend, **kwargs )

		# complete fetch task

		self.set_state_value( KEY_LAST_FETCH, datetime.utcnow().astimezone( UTC ).isoformat() ) # update fetch timestamp
		self.ctx.complete( 'done' )

		# download

		if not skip_download:
			self.ctx.start( f'downloading activity data from {self.display_name}', len( summaries ) )

			for summary in summaries:
				self.ctx.advance( f'{summary.uid}' )

				# find existing resources and attach it to summary
				existing = self.ctx.db.find_resources( uid=summary.uid )
				summary.resources = [r for r in existing if not(r.uid == summary.uid and r.path == summary.path)]

				downloaded = self.download( summary=summary, force=force, pretend=pretend, **kwargs )
				self.postprocess_resources( *downloaded, **kwargs )  # post process
				self.persist_resources( *downloaded, force=force, include_children=False, pretend=pretend, **kwargs )

			self.set_state_value( KEY_LAST_DOWNLOAD, datetime.utcnow().astimezone( UTC ).isoformat() )  # update download timestamp
			self.ctx.complete( 'done' )

		# link / vfs

		if not skip_link:
			pass # not yet implemented

	def link( self, activity: Activity, resource: Resource, force: bool, pretend: bool ) -> None:
		if resource.type in ['gpx', 'tcx'] and resource.status == 200: # todo: make linkable resources configurable
			src = self.path_for( resource=resource )
			dest = self.link_for( activity, resource )

			if not src or not dest:
				log.error( f"cannot determine source and/or destination for linking activity {activity.id}" )
				return

			if not src.exists() or src.is_dir():
				log.error( f"cannot link activity {activity.id}: source file {src} does not exist or is not a file" )
				return

			if not pretend:
				dest.parent.mkdir( parents=True, exist_ok=True )
				dest.unlink( missing_ok=True )
				dest.symlink_to( src )

			log.debug( f"linked resource for activity {activity.id}: {src} -> {dest}" )

	def setup( self, ctx: ApplicationContext ) -> None:
		pass

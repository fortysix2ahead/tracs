
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

from .activity import Activity
from .db import ActivityDb
from .plugin import Plugin
from .resources import Resource
from .config import ApplicationContext
from .config import GlobalConfig as gc
from .config import KEY_LAST_DOWNLOAD
from .config import KEY_LAST_FETCH
from .config import KEY_PLUGINS
from .registry import Registry

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( Plugin ):

	def __init__( self, **kwargs ):
		super().__init__( **kwargs )

		self._base_path = kwargs.pop( 'base_path' ) if 'base_path' in kwargs else None
		self._overlay_path = kwargs.pop( 'overlay_path' ) if 'overlay_path' in kwargs else None
		self._base_url = kwargs.pop( 'base_url' ) if 'base_url' in kwargs else None
		self._logged_in = False

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
	def filter_fetched( self, resources: List[Resource], **kwargs ) -> List[Resource]:
		if uid := kwargs.get( 'uid', None ):
			requested = next( (r for r in resources if r.uid == uid ), None )
			return [requested] if requested else []
		else:
			return resources

	# methods related to download()

	def download( self, activity: Optional[Activity] = None, summary: Optional[Resource] = None, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		"""
		Downloads related resources like GPX recordings based on a provided activity or summary resource.
		TODO: create a method for all services to ease implementation of subclasses.

		:param activity: activity
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

	def persist_resources( self, resources: Union[Resource, List[Resource]], force: bool, pretend: bool, **kwargs ) -> None:
		resources = [resources] if type( resources ) is Resource else resources
		if pretend:
			log.info( f'pretending to write resources' ) # todo: improve message
			return

		for r in resources:
			resource_list = [ r, *r.resources ]
			for rl in resource_list:
				path = self.path_for_resource( rl)
				path.parent.mkdir( parents=True, exist_ok=True )
				if not force and path.exists():
					continue

				try:
					path.write_bytes( rl.content )
					kwargs.get( 'ctx' ).db.insert_resource( rl )
				except TypeError:
					log.error( f'error writing resource data for resource {rl.uid}?{rl.path}', exc_info=True )

	def postprocess_resource( self, resource: Resource = None, **kwargs ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def create_activities( self, resource: Resource, **kwargs ) -> List[Activity]:
		if activity_cls := Registry.document_types.get( resource.type ):
			return [ activity_cls( raw=resource.raw, resources=[resource, *resource.resources] ) ]
		else:
			return []

	def postprocess_activities( self, *activities: Activity, **kwargs ) -> None:
		pass

	def persist_activities( self, *activities: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		for a in activities:
			self.upsert_activity( activity=a, force=force, pretend=pretend, **kwargs )

	def upsert_activity( self, activity: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		for r in activity.resources:
			if r.dirty and not pretend:
				r_db = self._ctx.db.find_resource( r.uid, r.path )
				if r_db: # todo: check if we can use db.upsert here
					self._ctx.db.update_resource( r )
				else:
					doc_id = self._ctx.db.insert_resource( r )
					log.info( f'created new resource: id = {doc_id}, uid = {r.uid}, path = {r.path}' )

		if not pretend:
			a_db = self._ctx.db.get( uid=activity.uid )
			if a_db:  # todo: check if we can use db.upsert here
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
		uid = kwargs.get( 'uid' )

		if uid:
			summary = self._db.get_resources_by_uid( uid )
		else:
			summaries = self.fetch( force, pretend, **kwargs ) # fetch 'main' resources for each activity
			summaries = self.filter_fetched( summaries, **kwargs ) # if only one resource was requested: filter out everything else

		# update fetch timestamp
		self.set_state_value( KEY_LAST_FETCH, datetime.utcnow().astimezone( UTC ).isoformat() )

		if not skip_download:
			self.ctx.start( f'downloading activity data from {self.display_name}', len( summaries ) )
			for summary in summaries:
				self.ctx.advance( f'{summary.uid}' )
				if not ( recordings := self._ctx.db.find_resource_group( summary.uid ).recordings() ) or force:
					self.download( summary=summary, force=force, pretend=pretend, **kwargs )
					self.postprocess_resource( resource=summary, **kwargs )  # post process
					self.persist_resources( resources=summary, force=force, pretend=pretend, **kwargs )

					activities = self.create_activities( resource=summary, **kwargs )
					self.postprocess_activities( *activities, **kwargs )
					self.persist_activities( *activities, force=force, pretend=pretend, **kwargs )

			self.ctx.complete( 'done' )

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

	def show_data( self, activity: Activity ) -> [[]]:
		return []

	@abstractmethod
	def setup( self, ctx: ApplicationContext ) -> None:
		pass

# ------------------------------------------------------------------------------

def download_activities( activities: List[Activity], ctx: ApplicationContext, force: bool = False, pretend: bool = False ):
	for a in activities:
		for uid in a.uids:
			resource_group = ctx.db.find_resource_group( uid )
			service = Registry.services.get( resource_group.summary().classifier )
			for recording in resource_group.recordings():
				path = Service.path_for_resource( recording )
				if not path.exists() or force:
					service.login() # login first ...
					service.download_resource( recording )

			a.resources = resource_group.recordings()
			service.persist_resource_data( a, force, pretend )

def link_activities( activities: [Activity], force: bool = False, pretend: bool = False ):
	_process_activities( activities, False, True, force, pretend )

def _process_activities( activities: List[Activity], ctx: ApplicationContext, download: bool, link: bool, force: bool, pretend: bool ):
	pass
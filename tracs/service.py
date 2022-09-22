
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

from dateutil.tz import UTC

from .activity import Activity
from .activity import Resource
from .base import Service as ServiceProtocol
from .config import ApplicationContext
from .config import GlobalConfig as gc
from .config import KEY_LAST_DOWNLOAD
from .config import KEY_LAST_FETCH
from .config import KEY_PLUGINS
from .plugins import Registry

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( ServiceProtocol ):

	def __init__( self, **kwargs ):
		self._name = kwargs.pop( 'name' ) if 'name' in kwargs else None
		self._display_name = kwargs.pop( 'display_name' ) if 'display_name' in kwargs else None
		self._base_path = kwargs.pop( 'base_path' ) if 'base_path' in kwargs else None
		self._base_url = kwargs.pop( 'base_url' ) if 'base_url' in kwargs else None
		self._cfg = kwargs.pop( 'config' ) if 'config' in kwargs else gc.cfg
		self._state = kwargs.pop( 'state' ) if 'state' in kwargs else gc.state
		self._logged_in = False

		# field for saving the current context, to access the context from sub-methods
		self._ctx: Optional[ApplicationContext] = None

		log.debug( f'service instance {self._name} created, with base path {self._base_path}' )

	# helpers for setting/getting plugin configuration/state values

	def cfg_value( self, key: str ) -> Any:
		return self._cfg[KEY_PLUGINS][self._name][key].get()

	def state_value( self, key: str ) -> Any:
		return self._state[KEY_PLUGINS][self._name][key].get()

	def set_cfg_value( self, key: str, value: Any ) -> None:
		self._cfg[KEY_PLUGINS][self._name][key] = value

	def set_state_value( self, key: str, value: Any ) -> None:
		self._state[KEY_PLUGINS][self._name][key] = value

	# properties

	@property
	def name( self ) -> str:
		return self._name

	@property
	def display_name( self ) -> str:
		return self._display_name

	@property
	def enabled( self ) -> bool:
		return True

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
	def base_url( self ) -> str:
		return self._base_url

	@property
	def db_dir( self ) -> Path:
		return self._cfg['db_dir'].get()

	@classmethod
	def path_for_resource( cls, resource: Resource ) -> Optional[Path]:
		classifier, raw_id = resource.classifier(), resource.raw_id()
		if service := Registry.services.get( classifier ):
			#return Path( service.path_for_id( raw_id, service.base_path ), resource.path )
			return service.path_for( resource=resource )

	def path_for_id( self, raw_id: int, base_path: Optional[Path] ) -> Path:
		_id = str( raw_id )
		rel_path = Path( _id[0], _id[1], _id[2], _id )
		return Path( base_path, rel_path ) if base_path else rel_path

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.

		:param activity: activity
		:param resource: resource
		:param ext: file extension for which the path should be returned, can be None
		:return: path of the activity in the local file system
		"""
		if activity:
			path = self.path_for_id( activity.raw_id, self.base_path )
			if ext:
				path = Path( path, f'{activity.raw_id}.{ext}' )
		elif resource:
			path = Path( self.path_for_id( resource.raw_id(), self.base_path ), resource.path )
		else:
			path = None

		return path

	def link_for( self, activity: Optional[Activity], resource: Optional[Resource], ext: Optional[str] = None ) -> Optional[Path]:
		ts = activity.time.strftime( '%Y%m%d%H%M%S' )
		path = Path( gc.lib_dir, ts[0:4], ts[4:6], ts[6:8] )
		if resource:
			path = Path( path, f'{ts[8:]}.{self.name}.{resource.type}' )
		elif ext:
			path = Path( path, f'{ts[8:]}.{self.name}.{ext}' )
		return path

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
		return [ r.raw_id() for r in self.fetch( force=False, pretend=False ) ]

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

	def persist_resource_data( self, activity: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		for r in activity.resources:
			path = self.path_for_resource( r )
			path.parent.mkdir( parents=True, exist_ok=True )
			if r.raw_data and r.status == 200:
				if not path.exists() or force:
					if not pretend:
						try:
							if type( r.raw_data ) is bytes:
								path.write_bytes( r.raw_data )
							elif type( r.raw_data ) is str:
								path.write_text( data=r.raw_data, encoding='UTF-8' )
							r.dirty = True
						except:
							log.error( f'skipping write of resource data for resource {r.path}' )
					else:
						log.info( f'pretending to write resource data to {path}' )

	def upsert_activity( self, activity: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		for r in activity.resources:
			if r.dirty and not pretend:
				r_db = self._ctx.db.find_resource( r.uid, r.path )
				if r_db: # todo: check if we can use db.upsert here
					self._ctx.db.update_resource( r )
				else:
					self._ctx.db.insert_resource( r )

		if not pretend:
			a_db = self._ctx.db.get( uid=activity.uid )
			if a_db:  # todo: check if we can use db.upsert here
				# self._ctx.db.update( activity ) # todo: what to do here?
				pass
			else:
				new_activity = Activity().init_from( activity )
				new_activity.uids = [activity.uid]
				self._ctx.db.insert( new_activity )

	def import_activities( self, force: bool = False, pretend: bool = False, **kwargs ):
		self._ctx: ApplicationContext = kwargs.get( 'ctx', None )
		skip_download = kwargs.get( 'skip_download', False )
		uid = kwargs.get( 'uid', None )

		# fetch 'main' resources for each activity
		summaries = self.fetch( force, pretend, **kwargs )

		# if only one resource was requested: filter out everything else
		if uid:
			requested = next( (r for r in summaries if r.uid == uid ), None )
			summaries = [requested] if requested else []

		# update fetch timestamp
		self._ctx.state[KEY_PLUGINS][self.name][KEY_LAST_FETCH] = datetime.utcnow().astimezone( UTC ).isoformat()

		for summary in summaries:
			recordings = []

			# do not download if skip flag is set
			if not skip_download:
				# download all additional resources for a certain local id/main resource
				if not ( recordings := self._ctx.db.find_resource_group( summary.uid ).recordings() ) or force:
					recordings = self.download( summary=summary, force=force, pretend=pretend, **kwargs )
					recordings = [ r for r in recordings if r.status == 200 ]
					self._ctx.state[KEY_PLUGINS][self.name][KEY_LAST_DOWNLOAD] = datetime.utcnow().astimezone( UTC ).isoformat()

			# create an activity out of the downloaded resources
			if activity_cls := Registry.document_types.get( summary.type ):
				activity = activity_cls( raw=summary.raw, resources=[summary, *recordings] )

				# persist all information
				if activity:
					self.persist_resource_data( activity=activity, force=force, pretend=pretend, **kwargs )
					self.upsert_activity( activity=activity, force=force, pretend=pretend, **kwargs )

	# not used at the moment ...

	# def _filter_fetched( self, fetched: Iterable[Activity], force: bool ) -> Tuple[List, List, List, List]:
	# 	all_existing: List[Activity] = list( self._ctx.db.find_by_classifier( self.name ) )
	# 	# old_new = [ ( next( ( e for e in existing if f.uid in e.uids ), None ), f ) for f in fetched ]
	#
	# 	added, updated, removed, unchanged = [], [], [], []
	#
	# 	for f in fetched:
	# 		# existing = next( (e for e in all_existing if f.uid in e.uids), None )
	# 		existing = self._ctx.db.get_by_uid( f.uid, True )
	# 		if not existing:
	# 			added.append( f )
	# 		else:
	# 			# all_existing.remove( existing ) # remove exiting activity from all_list, so we do not need to check it again
	# 			pass
	#
	# 			if force: # use newly fetched resources in case of force
	# 				existing.resources = f.resources
	# 				updated.append( existing )
	#
	# 			else: # check for delta
	# 				needs_update = False
	#
	# 				for r in f.resources:
	# 					existing_resource = next( ( re for re in existing.resources if r.path == re.path ), None )
	# 					if not existing_resource:
	# 						existing.resources.append( r )
	# 						needs_update = True
	#
	# 				updated.append( existing ) if needs_update else unchanged.append( existing )
	#
	# 	return added, updated, removed, unchanged

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
	def setup( self ) -> None:
		pass

# ------------------------------------------------------------------------------

def download_activities( activities: [Activity], force: bool = False, pretend: bool = False ):
	_process_activities( activities, True, False, force, pretend )

def link_activities( activities: [Activity], force: bool = False, pretend: bool = False ):
	_process_activities( activities, False, True, force, pretend )

def _process_activities( activities: [Activity], download: bool, link: bool, force: bool, pretend: bool ):
	for activity in activities:
		for uid in activity.uids:
			resources = gc.db.find_resources( uid )
			for r in resources:
				classifier, raw_id = r.uid.split( ':', maxsplit=1 )
				service = gc.app.services.get( classifier, None )

				if not service:
					log.warning( f"service {classifier} not found for activity {uid}, skipping ..." )
					continue

				if download:
					service.download( resource=r, force=force, pretend=pretend )
				if link:
					service.link( activity, r, force, pretend )

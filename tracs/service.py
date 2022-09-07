
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from logging import getLogger
from pathlib import Path
from sys import exit as sysexit
from typing import Any
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from dateutil.tz import UTC

from .activity import Activity
from .activity import Resource
from .base import Service as AbstractServiceClass
from .config import GlobalConfig as gc
from .config import KEY_LAST_DOWNLOAD
from .config import KEY_LAST_FETCH
from .config import KEY_PLUGINS
from .dataclasses import as_dict
from .utils import fmt

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( AbstractServiceClass ):

	def __init__( self, **kwargs ):
		self._name = kwargs.pop( 'name' ) if 'name' in kwargs else None
		self._display_name = kwargs.pop( 'display_name' ) if 'display_name' in kwargs else None
		self._base_path = kwargs.pop( 'base_path' ) if 'base_path' in kwargs else None
		self._cfg = kwargs.pop( 'config' ) if 'config' in kwargs else gc.cfg
		self._state = kwargs.pop( 'state' ) if 'state' in kwargs else gc.state
		self._logged_in = False

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
	def db_dir( self ) -> Path:
		return self._cfg['db_dir'].get()

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.

		:param activity: activity
		:param resource: resource
		:param ext: file extension for which the path should be returned, can be None
		:return: path of the activity in the local file system
		"""
		_id = str( activity.raw_id ) if activity else resource.uid.split( ':', maxsplit=1 )[1]
		path = Path( self.base_path, _id[0], _id[1], _id[2], _id )
		if resource:
			path = Path( path, resource.path )
		elif ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def link_for( self, a: Activity, r: Resource, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the link path for an activity.

		:param a: activity to link
		:param ext: file extension
		:return: link path for activity
		"""
		ts = a.time.strftime( '%Y%m%d%H%M%S' )
		path = Path( gc.lib_dir, ts[0:4], ts[4:6], ts[6:8] )
		if r:
			path = Path( path, f'{ts[8:]}.{self.name}.{r.type}' )
		elif ext:
			path = Path( path, f'{ts[8:]}.{self.name}.{ext}' )
		return path

	def fetch( self, force: bool = False, **kwargs ) -> List[Activity]:
		if not self.logged_in:
			self._logged_in = self.login()

		if not self.logged_in:
			log.error( f"unable to login to service {self.display_name}, exiting ..." )
			sysexit( -1 )

		new_activities = []
		updated_activities = []
		#fetched_activities = []

		fetched = self._fetch( force=force, kwargs=kwargs.items() )
		existing = list( gc.db.find_by_classifier( self.name ) )
		old_new = [ ( next( ( e for e in existing if f.uid in e.uids ), None ), f ) for f in fetched ]

		for _old, _new in old_new:
			# insert if no old activity exists
			if not _old:
				_new_activity = Activity().init_from( _new )
				_new_activity.uids.append( _new.uid ) # todo: this might be moved to init_from
				doc_id = gc.db.insert( _new_activity )
				new_activities.append( _new_activity )
				log.debug( f'created new activity {doc_id} (id {_new_activity.id}), time = {fmt( _new_activity.time )}')

			# update if forced
			elif _old and force:
				_new.doc_id = _old.doc_id
				gc.db.update( _new )
				updated_activities.append( _new )
				log.debug( f'updated activity {_old.doc_uid}, time = {fmt( _new.time )}')

			# write raw data of resources
			for r in _new.resources:
				path = Path( self.path_for( _new ), r.path )
				if not path.exists() or force:
					path.parent.mkdir( parents=True, exist_ok=True )
					if type( r.raw_data ) is bytes:
						path.write_bytes( r.raw_data )
					elif type( r.raw_data ) is str:
						path.write_text( data=r.raw_data, encoding='UTF-8' )
					else:
						log.debug( f'skipping write of resource data for activity {_new.uid}, resource {r.path}, status {r.status}, type of data is neither str or bytes' )

			# write resource information to resource db
			new_resources = []
			existing_resources = gc.db.find_resources( _new.uid )
			for r in _new.resources:
				if not next( (e for e in existing_resources if e.get( 'path' ) == r.path), None ):
					new_resources.append( as_dict( r ) )

			gc.db.resources.insert_multiple( new_resources )

		log.info( f"fetched activities from {self.display_name}: {len( new_activities )} new, {len( updated_activities )} updated" )

		# update last_fetch in state
		gc.state[KEY_PLUGINS][self.name][KEY_LAST_FETCH] = datetime.utcnow().astimezone( UTC ).isoformat()

		return new_activities

	@abstractmethod
	def _fetch( self, force: bool = False, **kwargs ) -> Iterable[Activity]:
		"""
		Called by fetch(). This method has to be implemented by a service class. It shall fetch information concerning
		activities from external service and create activities out of it. The newly created activities will be matched
		against the internal database and inserted if necessary.

		:param force: flag to signal force execution
		:param kwargs: additional parameters
		:return: list of fetched activities
		"""
		pass

	def download( self, resource: Resource = None, force: bool = False, pretend: bool = False ) -> None:
		if not self.login():
			log.error( f"unable to login to service {self.display_name}, exiting ..." )
			sysexit( -1 )

		# don't care about raw resources
		if resource.type == 'raw':
			log.debug( f"skipped download of {resource.path} for activity {resource.uid}: raw resources will not be processed by download" )
			return

		if resource.status in [204, 404]:  # file does not exist on server -> do nothing
			log.debug( f"skipped download of {resource.path} for activity {resource.uid}: file does not exist on server" )
			return

		if resource.status == 200 and not force:
			log.debug( f"skipped download of {resource.path} for activity {resource.uid}: marked as already existing" )
			return

		if resource.status == 100 or (resource.status == 200 and force):
			path = self.path_for( resource=resource )
			if path.exists() and not force:  # file exists already and no force to re-download -> do nothing
				log.debug( f"skipped download of {resource.path} for activity {resource.uid}: file already exists" )
				return

			content, status = self.download_resource( resource )

			if status == 200:
				path.parent.mkdir( parents=True, exist_ok=True )
				path.write_bytes( content )
				log.info( f"downloaded {resource.type} for activity {resource.uid} to {path}" )

			elif status == 204:
				log.error( f"failed to download {resource.type} for activity {resource.uid}, service responded with HTTP 200, but without content" )

			elif status == 404:
				log.error( f"failed to download {resource.type} for activity {resource.uid}, service responded with HTTP 404 - not found" )

			else:
				log.error( f"failed to download {resource.type} for activity {resource.uid}, service responded with HTTP {resource.status}" )

			resource.status = status

			gc.db.update_resource( resource ) # update status of resource in db

		# update last_download in state
		gc.state[KEY_PLUGINS][self.name][KEY_LAST_DOWNLOAD] = datetime.utcnow().astimezone( UTC ).isoformat()

	@abstractmethod
	def download_resource( self, resource: Resource ) -> Tuple[Any, int]:
		pass

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

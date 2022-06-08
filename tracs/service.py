
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

from .base import Activity
from .base import Resource
from .base import Service as AbstractServiceClass
from .config import ApplicationConfig as cfg
from .config import ApplicationState as state
from .config import GlobalConfig as gc
from .config import KEY_PLUGINS

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( AbstractServiceClass ):

	def __init__( self, **kwargs ):
		self._name = kwargs.pop( 'name' ) if 'name' in kwargs else None
		self._display_name = kwargs.pop( 'display_name' ) if 'display_name' in kwargs else None
		#self._cfg = kwargs.pop( 'config' ) if 'config' in kwargs else cfg[KEY_PLUGINS][self._name]
		#self._state = kwargs.pop( 'state' ) if 'state' in kwargs else state[KEY_PLUGINS][self._name]
		self._logged_in = False

	def cfg_value( self, key: str ) -> Any:
		return cfg[KEY_PLUGINS][self._name][key].get()

	def state_value( self, key: str ) -> Any:
		return state[KEY_PLUGINS][self._name][key].get()

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
	def db_dir( self ) -> Path:
		return cfg['db_dir'].get()

	def path_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.

		:param a: activity
		:param ext: file extension for which the path should be returned, can be None
		:return: path of the activity in the local file system
		"""
		id = str( a.raw_id )
		path = Path( gc.db_dir, self.name, id[0], id[1], id[2], id )
		if ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def link_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the link path for an activity.

		:param a: activity to link
		:param ext: file extension
		:return: link path for activity
		"""
		ts = a['time'].strftime( '%Y%m%d%H%M%S' ) if a['time'] else None
		if not ts:
			return None

		path = Path( gc.lib_dir, ts[0:4], ts[4:6], ts[6:8] )
		if ext:
			path = Path( path, f'{ts[8:]}.{self.name}.{ext}' )
		return path

	def fetch( self, fetch_all: bool ) -> List[Activity]:
		if not self.logged_in:
			self._logged_in = self.login()

		if not self.logged_in:
			log.error( f"unable to login to service {self.display_name}, exiting ..." )
			sysexit( -1 )

		if fetch_all:
			if not (fetch_from := cfg['fetch_from'].get( int )):
				fetch_from = datetime.utcnow().year - 10
			fetch_to = datetime.utcnow().year + 1
			fetch_range = range( fetch_from, fetch_to )
		else:
			latest = gc.db.find_last( self.name )
			if latest:
				fetch_range = range( latest.utctime.year, datetime.utcnow().year + 1 )
			else:
				fetch_range = [datetime.utcnow().year]

		log.debug( f"fetch range for {self.display_name} is {fetch_range}" )

		new_activities = []
		updated_activities = []
		#fetched_activities = []

		for year in fetch_range:
			log.info( f"fetching activities from {self.display_name} for {year} ..." )
			fetched = self._fetch( year )
			for na in fetched: # na = new activity
				# create/update external activity in service table
				oa = gc.db.get( raw_id=na['raw_id'], service_name=self.name )
				if oa is None:
					gc.db.insert( na )
					new_activities.append( na )
					log.debug( f'created new {self.name} activity {na.id}' )
				else:
					if cfg['force'].get( bool ): # update in case it was forced
						na.doc_id = oa.doc_id
						gc.db.update( na )
						updated_activities.append( na )
						log.debug( f'updated {self.name} activity {na.id}' )

		log.info( f"fetched activities from {self.display_name}: {len( new_activities )} new, {len( updated_activities )} updated" )

		return new_activities

	@abstractmethod
	def _fetch( self, year: int ) -> Iterable[Activity]:
		"""
		Called by fetch(). This method has to be implemented by a service class. It shall fetch information concerning
		activities from external service and create activities out of it. The newly created activities will be matched
		against the internal database and inserted if necessary.

		:param year: year for which to fetch activities
		:return: list of fetched activities
		"""
		pass

	def download( self, activity: Activity, force: bool, pretend: bool ) -> None:
		log.debug( f"attempting to download activity {activity.raw_id} from {self.name}" )

		if not self.logged_in:
			self._logged_in = self.login()

		if not self.logged_in:
			log.error( f"unable to login to service {self.display_name}, exiting ..." )
			sysexit( -1 )

		for r in activity.resources:
			if r.status in [204, 404]:  # file does not exist on server -> do nothing
				log.debug( f"skipped download of {r.type} for {self.name} activity {activity.raw_id}: file does not exist on server" )
				continue

			if not (path := self.path_for( activity, r.type )):
				log.error( f'unable to determine path for {r.type} for {self.name} activity {activity.raw_id}' )
				continue

			if path.exists() and not force:  # file exists already and no force to re-download -> do nothing
				if r.status != 200:  # mark file as 'exists on server' if not already done
					r.status = 200
					gc.db.update( activity )
				log.debug( f"skipped download of {r.type} for {self.name} activity {activity.raw_id}: file already exists" )
				continue

			if not path.exists() or force:  # either file does not exist or it's a forced download, todo: multipart support
				content, status = self._download_file( activity, r )
				if status == 200 and len( content ) == 0:
					status = 204

				if status == 200:
					path.parent.mkdir( parents=True, exist_ok=True )
					path.write_bytes( content )
					log.info( f"downloaded {r.type} for {self.name} activity {activity.raw_id} to {path}" )

				elif status == 204:
					log.error( f"failed to download {r.type} for {self.name} activity {activity.raw_id}, service responded with HTTP 200, but without content" )

				elif status == 404:
					log.error( f"failed to download {r.type} for {self.name} activity {activity.raw_id}, service responded with HTTP 404 - not found" )

				else:
					log.error( f"failed to download {r.type} for {self.name} activity {activity.raw_id}, service responded with HTTP {r.status}" )

				r.status = status
				gc.db.update( activity )

	@abstractmethod
	def _download_file( self, activity: Activity, resource: Resource ) -> Tuple[Any, int]:
		pass

	def link( self, activity: Activity, force: bool, pretend: bool ) -> None:
		for r in activity.resources:
			src = self.path_for( activity, r.type )
			dest = self.link_for( activity, r.type )

			if not src or not dest:
				log.error( f"cannot determine source and/or destination for linking activity {activity.id}" )
				continue

			if not src.exists() or src.is_dir():
				log.error( f"cannot link activity {activity.id}: source file {src} does not exist or is not a file" )
				continue

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

def download_activities( activities: [Activity] ):
	_process_activities( activities, True, False )

def link_activities( activities: [Activity] ):
	_process_activities( activities, False, True )

def _process_activities( activities: [Activity], download: bool, link: bool ):
	force = cfg['force'].get( bool )
	pretend = cfg['pretend'].get( bool )
	for activity in activities:
		if activity.is_group:
			_queue = [gc.db.get( doc_id=doc_id ) for doc_id in activity.group_for]
		else:
			_queue = [activity]

		for a in _queue:
			service = gc.app.services.get( a.service, None )

			if not service:
				log.warning( f"service {a.service} not found for activity {a.id}, skipping ..." )
				continue

			if download:
				service.download( a, force, pretend )
			if link:
				service.link( a, force, pretend )

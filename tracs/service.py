
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

from .base import Activity
from .base import Resource
from .base import Service as AbstractServiceClass
from .config import GlobalConfig as gc
from .config import KEY_LAST_DOWNLOAD
from .config import KEY_LAST_FETCH
from .config import KEY_PLUGINS
from .utils import fmt

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( AbstractServiceClass ):

	def __init__( self, **kwargs ):
		self._name = kwargs.pop( 'name' ) if 'name' in kwargs else None
		self._display_name = kwargs.pop( 'display_name' ) if 'display_name' in kwargs else None
		self._cfg = kwargs.pop( 'config' ) if 'config' in kwargs else gc.cfg
		self._state = kwargs.pop( 'state' ) if 'state' in kwargs else gc.state
		self._logged_in = False

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
	def db_dir( self ) -> Path:
		return self._cfg['db_dir'].get()

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

	def fetch( self, force: bool = False ) -> List[Activity]:
		if not self.logged_in:
			self._logged_in = self.login()

		if not self.logged_in:
			log.error( f"unable to login to service {self.display_name}, exiting ..." )
			sysexit( -1 )

		new_activities = []
		updated_activities = []
		#fetched_activities = []

		fetched = self._fetch( force=force )
		existing = list( gc.db.find( f'classifier:{self.name}', False, True, True ) )
		old_new = [ ( next( (e for e in existing if e.uid == f.uid), None ), f ) for f in fetched ]

		for _old, _new in old_new:
			# insert if no old activity exists
			if not _old:
				doc_id = gc.db.insert( _new )
				new_activities.append( _new )
				# todo: log statement might cause problem when certain unicode chars are contained in name
				# log.debug( f'created new activity {_new.uid} (id {doc_id}), name = {_new["name"]}, time = {fmt( _new["localtime"] )}')
				log.debug( f'created new activity {_new.uid} (id {doc_id}), time = {fmt( _new["localtime"] )}')
			# update if forced
			elif _old and force:
				_new.doc_id = _old.doc_id
				gc.db.update( _new )
				updated_activities.append( _new )
				# todo: log statement might cause problem when certain unicode chars are contained in name
				#log.debug( f'updated activity {_new.uid} (id {_new.doc_id}), name = {_new["name"]}, time = {fmt( _new["localtime"] )}')
				log.debug( f'updated activity {_new.uid} (id {_new.doc_id}), time = {fmt( _new["localtime"] )}')

			if _new.raw_data and _new.raw_name:
				path = Path( self.path_for( _new ), _new.raw_name )
				if not path.exists() or force:
					path.parent.mkdir( parents=True, exist_ok=True )
					if type( _new.raw_data ) is bytes:
						path.write_bytes( _new.raw_data )
					elif type( _new.raw_data ) is str:
						path.write_text( data=_new.raw_data, encoding='UTF-8' )
					else:
						log.error( f'error writing raw data for activity {_new.uid}, type of data is neither str or bytes' )

		log.info( f"fetched activities from {self.display_name}: {len( new_activities )} new, {len( updated_activities )} updated" )

		# update last_fetch in state
		gc.state[KEY_PLUGINS][self.name][KEY_LAST_FETCH] = datetime.utcnow().astimezone( UTC ).isoformat()

		return new_activities

	@abstractmethod
	def _fetch( self, force: bool = False ) -> Iterable[Activity]:
		"""
		Called by fetch(). This method has to be implemented by a service class. It shall fetch information concerning
		activities from external service and create activities out of it. The newly created activities will be matched
		against the internal database and inserted if necessary.

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
			# todo: r is currently a dict -> need to change that later to Resource
			if r['status'] in [204, 404]:  # file does not exist on server -> do nothing
				log.debug( f"skipped download of {r.type} for {self.name} activity {activity.raw_id}: file does not exist on server" )
				continue

			if not (path := self.path_for( activity, r['type'] )):
				log.error( f'unable to determine path for {r["type"]} for {self.name} activity {activity.raw_id}' )
				continue

			if path.exists() and not force:  # file exists already and no force to re-download -> do nothing
				if r['status'] != 200:  # mark file as 'exists on server' if not already done
					r['status'] = 200
					gc.db.update( activity )
				log.debug( f"skipped download of {r['type']} for {self.name} activity {activity.raw_id}: file already exists' )" )
				continue

			if not path.exists() or force:  # either file does not exist or it's a forced download, todo: multipart support
				content, status = self._download_file( activity, r )
				if status == 200 and len( content ) == 0:
					status = 204

				if status == 200:
					path.parent.mkdir( parents=True, exist_ok=True )
					path.write_bytes( content )
					log.info( f"downloaded {r['type']} for {self.name} activity {activity.raw_id} to {path}" )

				elif status == 204:
					log.error( f"failed to download {r['type']} for {self.name} activity {activity.raw_id}, service responded with HTTP 200, but without content" )

				elif status == 404:
					log.error( f"failed to download {r['type']} for {self.name} activity {activity.raw_id}, service responded with HTTP 404 - not found" )

				else:
					log.error( f"failed to download {r['type']} for {self.name} activity {activity.raw_id}, service responded with HTTP {r['status']}" )

				r['status'] = status

				if activity.id != 0:
					gc.db.update( activity )
				else:
					log.warning( f'unable to update resource status for activity {activity.uid}: db id is 0' )

		# update last_download in state
		gc.state[KEY_PLUGINS][self.name][KEY_LAST_DOWNLOAD] = datetime.utcnow().astimezone( UTC ).isoformat()

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
	force = gc.cfg['force'].get( bool )
	pretend = gc.cfg['pretend'].get( bool )
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

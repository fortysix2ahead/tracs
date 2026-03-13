
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timedelta
from logging import getLogger
from pathlib import Path
from typing import Any, cast, ClassVar, Dict, List, Optional, Type, Union

from arrow import utcnow
from attrs import define, field
from dateutil.tz import UTC
from fs.base import FS
from fs.copy import copy_file
from fs.errors import NoSysPath, ResourceNotFound
from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.path import basename, combine, dirname, isabs, join, parts, split
from more_itertools.recipes import first_true

from tracs.activity import Activities, Activity
from tracs.constants import *
from tracs.db import ActivityDb
from tracs.plugin import Plugin
from tracs.resources import Resource, Resources
from tracs.uid import UID

log = getLogger( __name__ )

# ---- base class for a service ----

class Service( Plugin ):

	SERVICE_NAME: ClassVar[str] = '__UNKNOWN__' # this needs to be set to a proper value in subclasses

	def __init__( self, *args, **kwargs ):
		super().__init__( *args, **kwargs )

		# paths + plugin filesystem area
		# providing parameters via kwargs is for testing only and is not supposed to be used in production
		# there's no check for ctx being null as a service shall not exist without a context

		self._user_id = kwargs.get( CFG_USER_ID ) or self._cfg.get( CFG_USER_ID )
		self._db_path = kwargs.get( CFG_DB_PATH ) or self._cfg.get( CFG_DB_PATH )

		# plugin fs
		if kwargs.get( CFG_FS ):
			self._fs: FS = kwargs.get( CFG_FS )
		elif self._db_path:
			self._fs: FS = self.ctx.plugin_fs( slug=self._db_path )
		else:
			self._fs: FS = self.ctx.plugin_fs( self.name, self._user_id )

		log.debug( f'service instance {self.name} configured to use plugin fs = {self._fs}' )

		self._takeout_path = kwargs.get( CFG_TAKEOUT_PATH ) or self._cfg.get( CFG_TAKEOUT_PATH )
		self._takeout_fs: FS = kwargs.get( CFG_TAKEOUT_FS )
		log.debug( f'service instance {self.name} uses takeout path = {self._takeout_path}' )

		# common fs being equal for all plugins
		self._dbfs = kwargs.get( CFG_DB_FS ) or self.ctx.db_fs
		self._tmpfs = kwargs.get( CFG_TMP_FS ) or self.ctx.tmp_fs
		self._rootfs = OSFS( '/' )  # needed ?
		self._base_url = kwargs.get( CFG_BASE_URL )

		self._logged_in: bool = False

		log.debug( f'service instance {self.name} created with fs = {self._fs}' )

	# properties

	@property
	def logged_in( self ) -> bool:
		return self._logged_in

	@property
	def base_path( self ) -> Path:
		return Path( self.fs.getsyspath( '/' ) )

	@property
	def overlay_path( self ) -> Path:
		return Path( self.fs.getsyspath( '/' ) ) # todo: this is not yet correct

	@property
	def base_url( self ) -> str:
		return self._base_url

	@property # todo: remove later for self.db
	def _db( self ) -> ActivityDb:
		return self.db

	# fs properties (read-only)

	@property
	def fs( self ) -> FS:
		return self._fs

	@property
	def dbfs( self ) -> FS:
		return self._dbfs

	@property
	def base_fs( self ) -> FS:
		return cast( MultiFS, self._fs ).get_fs( DB_DIRNAME )

	@property
	def overlay_fs( self ) -> FS:
		return cast( MultiFS, self._fs ).get_fs( OVERLAY_DIRNAME )

	# class methods for helping with various things

	@classmethod
	def path_for_resource( cls, resource: Resource, absolute: bool = True, as_path: bool = True, ignore_overlay: bool = True ) -> Union[Path, str]:
		try:
			service = current_ctx().registry.services.get( resource.classifier )
			return service.path_for( resource=resource, absolute=absolute, as_path=as_path, ignore_overlay=ignore_overlay )
		except AttributeError:
			log.error( f'unable to calculate resource path for {resource}', exc_info=True )

	@staticmethod
	def as_activity( resource: Resource, **kwargs ) -> Activity:
		"""
		Loads a resource and transforms it into an activity by using the importer indicated by the resource type.
		"""
		Service.load_resources( None, resource )
		importer = kwargs.get( 'ctx', current_ctx() ).registry.importer_for( resource.type )
		activity = importer.load_as_activity( resource=resource )
		activity.metadata.created = utcnow().datetime
		activity.resources = Resources( resource )
		return activity

	@staticmethod
	def as_activity_from( resource: Resource, **kwargs ) -> Optional[Activity]:
		"""
		Loads a resource to an activity in a 'lazy' manner, reusing the existing content of the resource.
		"""
		registry = kwargs.get( 'registry', current_ctx().registry )
		return registry.importer_for( resource.type ).load_as_activity( resource=resource, **kwargs )

	@staticmethod
	def load_resources( activity: Optional[Activity] = None, *resources: Resource, **kwargs ):
		"""
		Loads the provided resources, either from the list or from the activity. This will only load the content, the activity will not be updated.

		:param activity: activity, which resources shall be loaded
		:param resources: list of resources to load
		:param kwargs: ctx: context to use, if omitted current_ctx() will be used
		:return:
		"""
		ctx = kwargs.get( 'ctx', current_ctx() )
		resources = activity.resources if activity else resources or []
		for r in resources:
			if importer := ctx.registry.importer_for( r.type ):
				importer.load( path=r.path, fs=ctx.db_fs, resource=r ) # todo: implement exception handling here

	# service methods

	def path_for_id( self, local_id: Union[int, str], base_path: Optional[str] = None, user_id: Optional[str] = None,
	                 resource_path: Optional[str] = None, as_path: bool = False ) -> Union[Path, str]:
		"""Calculates the path for a resource based on the provided information.
		Note that this path is relative, but not yet relative to something particular,
		i.e. it might be relative to DB FS if a base path is provided.
		This calls _path_for_id() which might be overwritten in subclasses.
		Also note that this does not take service name or service user into account! Use svc_path_for_id() for this.

		:param local_id: local id of a resource
		:param base_path: base path is prepended to the calculated path, if provided. Usually this will be the name of the service instance.
		:param user_id: the user id is used as the second segment of the path, if provided.
		:param resource_path: the path of the resource
		:param as_path: if true, returns a Path instead of a string
		:return: the calculated path
		"""
		path = self._path_for_id( local_id )
		path = combine( user_id, path ) if user_id else path
		path = combine( base_path, path ) if base_path else path
		path = combine( path, resource_path ) if resource_path else path
		return Path( path ) if as_path else path

	# noinspection PyMethodMayBeStatic
	def _path_for_id( self, local_id: int|str ) -> str:
		"""Helper which transforms a provided ID into a default path.
		The default behaviour is ABCD -> A/B/C/ABCD. Right justification will be applied (zero-based).

		:param local_id: id to transform
		:return: transformed id
		"""
		return path_for_id( local_id )

	def svc_path_for_id( self, local_id: Union[int, str], resource_path: Optional[str] = None, as_path: bool = False ):
		"""Returns the path for an id and takes service name and user into account (if set).

		:param local_id: id to transform
		:param resource_path: resource path
		:param as_path: if true, returns a Path instead of a string
		:return: transformed id
		"""
		return self.path_for_id( local_id, self.name, self._user_id, resource_path, as_path )

	def path_for( self, resource: Resource, absolute: bool = False, omit_classifier: bool = False,
	              ignore_overlay: bool = True, as_path: bool = False ) -> Optional[Path|str]:
		"""
		Returns the path in the local file system for a provided resource.

		:param resource: resource for which the path shall be calculated
		:param ignore_overlay: if True ignores the overlay
		:param absolute: if True returns an absolute path
		:param omit_classifier: if True, the relative path will not include the leading name of the service
		:param as_path: if True, return the result as Path
		:return: path of the resource in the local file system
		"""
		uid = resource.uid
		path = resource.path or resource.uid.path
		head, tail = split( path )

		if isabs( path ):
			return path

		if not head:
			path = self.svc_path_for_id( uid.local_id, path, False )

		if omit_classifier and not absolute:
			path = join( *parts( path )[2:] )

		if absolute:
			try:
				path = self.dbfs.getsyspath( path )
			except (AttributeError, ResourceNotFound, NoSysPath ):
				path = f'/{DB_DIRNAME}/{path}'

		return Path( path ) if as_path else path

	def url_for( self, activity: Optional[Activity] = None, resource: Optional[Resource] = None, local_id: Optional[int] = None ) -> Optional[str]:
		url = None

		if local_id:
			url = self.url_for_id( local_id )
		elif resource and resource.classifier == self.name:
			url = self.url_for_resource_type( resource.local_id, resource.type )
		elif activity:
			try:
				uid = activity.as_uid()
				if uid.classifier == self.name:
					url = self.url_for_id( uid.local_id )
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

	def import_activities( self, force: bool = False, pretend: bool = False, **kwargs ) -> Activities:
		fetch_all = kwargs.get( 'fetch_all' ) or self.ctx.config['import'].fetch_all
		first_year = self.ctx.config['import'].first_year
		days_range = self.ctx.config['import'].range

		if fetch_all:
			range_from = datetime( first_year, 1, 1, tzinfo=UTC )
		else:
			range_from = datetime.now( UTC ) - timedelta( days = days_range )
		range_to = datetime.now( UTC ) + timedelta( days=1 )

		if kwargs.get( CFG_FROM_TAKEOUTS ):
			if not self._takeout_fs:
				if self._takeout_path:
					self._takeout_fs = self.ctx.takeout_fs( slug=self._takeout_path )
				else:
					self._takeout_fs = self.ctx.takeout_fs( self.name, self._user_id )


			src_fs: FS = self._takeout_fs
			src_path: str = None

		classifier = self.cfg_value( CFG_CLASSIFIER ) or self.name
		type = kwargs.get( 'type' )

		skip_fetch = kwargs.get( 'skip_fetch', False )
		skip_download = kwargs.get( 'skip_download', False )

		dst_fs = self.ctx.import_fs()

		# actual import from local fs or remote
		if src_fs and self.supports_fs_import( src_fs, src_path ):
			log.debug( f'service {self.name} supports import from {src_fs.getsyspath( "" )}' )
			activities = self.import_from_fs( src_fs, dst_fs, path=src_path, classifier=classifier, type=type )

		elif self.supports_remote_import():
			log.debug( f'service {self.name} supports remote import' )
			activities = self.import_from_remote( dst_fs, range_from=range_from, range_to=range_to )

		else:
			log.info( f'service [bold]{self.name}[/bold] does not support neither remote nor local import from {src_fs} or no suitable file(s) to import have been found' )
			activities = Activities()

		# post-process activities
		for a in activities:
			# move imported resources
			for r in a.resources:
				if force or not self.ctx.db_fs.exists( r.path ):
					try:
						self.ctx.db_fs.makedirs( dirname( r.path ), recreate=True )
						copy_file( dst_fs, r.path, self.ctx.db_fs, r.path, preserve_time=True )
						dst_fs.remove( r.path )
						# don't know why move_file fails, maybe a bug?
						# move_file( import_fs, r.path, ctx.db_fs, r.path, preserve_time=True )
						log.debug( f'imported resource {UID( a.uid.classifier, a.uid.local_id, path=basename( r.path ) )}' )

					except ResourceNotFound:
						log.error( f'error importing from resource {UID( a.uid.classifier, a.uid.local_id, path=basename( r.path ) )}' )

				else:
					log.info( f'skipping import of resource {r}, file already exists, use option -f/--force to force overwrite' )

			# insert / upsert newly created activities
			if self.ctx.db.contains_activity( a.uid ):
				self.ctx.db.upsert( a )
			else:
				self.ctx.db.insert( a )

		# commit changes to db
		if len( activities ) > 0:
			self.ctx.db.save()

		# return imported activities
		return activities

	def supports_fs_import( self, fs: FS | None, path: str | None ) -> bool:
		return False

	def import_from_fs( self, src_fs: FS, dst_fs: FS, **kwargs ) -> Activities:
		return Activities()

	def supports_remote_import( self ) -> bool:
		return False

	def import_from_remote( self, dst_fs: FS, range_from: datetime, range_to: datetime ) -> Activities:
		return Activities()

@define
class ServiceManager:

	services_classes: Dict[str, Type[Service]] = field( factory=dict )
	services: Dict[str, Service] = field( factory=dict )

	def add_class( self, cls: Type[Service] ):
		self.services_classes[f'{cls.__module__}.{cls.__name__}'] = cls

	def add( self, service_instance: Service ) -> None:
		"""
		Adds an existing service to the manager.

		:param service_instance: service instance to add
		:return: None
		"""
		self.services[service_instance.name] = service_instance

	def add_from( self, ctx, name: str, config: Dict[str, Any] ):
		service_cls = first_true( self.services_classes.values(), pred=lambda sc: sc.SERVICE_NAME == config.get( 'type' ) )
		if service_cls:
			cfg_dict = config | { CFG_CTX: ctx, 'name': name }
			cfg_dict.pop( 'type' )
			self.services[name] = service_cls( **cfg_dict )
		else:
			log.error( f'unable to find service class for service type {name}' )

	def get( self, name: str ) -> Service|None:
		return self.services.get( name )

	def service_names( self ) -> List[str]:
		return list( self.services.keys() )

	# noinspection PyMethodMayBeStatic
	def path_for( self, resource: Resource ) -> str:
		return resource.path # todo: this might be removed

	def url_for( self, uid: UID|str ) -> Optional[str]:
		uid: UID = UID( uid ) if isinstance( uid, str ) else uid
		if service := self.services.get( uid.classifier ):
			return service.url_for( local_id=uid.local_id )
		else:
			return None

# helper functions

def path_for_id( local_id: int|str ) -> str:
	local_id_rjust = str( local_id ).rjust( 3, '0' )
	return f'{local_id_rjust[0]}/{local_id_rjust[1]}/{local_id_rjust[2]}/{local_id}'

def path_for_date( date_id: Union[int, str, datetime] ) -> str:
	if isinstance( date_id, int ):
		date_id = str( date_id )
	elif isinstance( date_id, datetime ):
		date_id = date_id.strftime( "%y%m%d%H%M%S" )

	date_id = str( date_id ).rjust( 6, '0' )
	return f'{date_id[0:2]}/{date_id[2:4]}/{date_id[4:6]}/{date_id}'

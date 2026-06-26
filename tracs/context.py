
from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os.path import abspath, expanduser, expandvars, split
from pathlib import Path
from typing import Any, cast, Dict, Optional, Tuple

from attrs import define, field
from dateutil.tz import tzlocal
from dynaconf import Dynaconf as Configuration
from dynaconf.utils.boxing import DynaBox
from dynaconf.vendor.box.exceptions import BoxKeyError
from fs.appfs import UserCacheFS, UserConfigFS, UserDataFS, UserLogFS
from fs.base import FS
from fs.errors import NoSysPath, ResourceNotFound
from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.path import dirname
from fs.subfs import SubFS
from yaml import safe_dump

from tracs.__log__ import LogManager
from tracs.constants import *
from tracs.pluginmgr import PluginManager, Registry, ServiceManager
from tracs.protocols import ActivityDb, RuleParser
from tracs.utils import fs_to_str

log = getLogger( __name__ )

# default user locations are the following

# Mac OS:
# UserConfigFS ~/Application Support/tracs/
# UserDataFS ~/Library/Application Support/tracs/
# SiteDataFS /Library/Application Support/tracs
# SiteConfigFS /Library/Application Support/tracs
# UserCacheFS ~/Library/Caches/tracs/
# UserLogFS ~/Library/Logs/tracs/

ROOT_FS = OSFS( root_path='/', expand_vars=True )

USER_CONFIG_FS: FS = UserConfigFS( APPNAME, create=True )
USER_DATA_FS: FS = UserDataFS( APPNAME, create=True )
USER_CACHE_FS: FS = UserCacheFS( APPNAME, create=True )
USER_LOG_FS: FS = UserLogFS( APPNAME, create=True )

def _set_config_fs( inst, att, val ):
	if isinstance( val, FS ):
		value = val
	elif isinstance( val, str ):
		path = abspath( expandvars( expanduser( val ) ) )
		head, tail = split( path )
		value = OSFS( root_path=head if tail == CONFIG_FILENAME else path, expand_vars=True, create=True )
	else:
		value = UserConfigFS( APPNAME, create=True )

	# noinspection PyProtectedMember
	inst._setup_aux_fs( config_fs=value )

	return value

def _set_lib_fs( inst, att, val ):
	if isinstance( val, FS ):
		value: FS = val
	elif isinstance( val, str ):
		value = OSFS( root_path=abspath( expandvars( expanduser( val ) ) ), expand_vars=True, create=True )
	else:
		value: FS = UserDataFS( APPNAME, create=True )

	# noinspection PyProtectedMember
	inst._setup_aux_fs( lib_fs=value )

	return value

@define
class ApplicationContext:

	# configuration + state
	config: Configuration = field( default=None )
	state: Configuration = field( default=None )

	# configuration fs
#	config_fs: FS = field( default=USER_CONFIG_FS, on_setattr=_set_config_fs )
	config_fs: FS = field( default=USER_CONFIG_FS )

	# library fs
#	lib_fs: FS = field( default=USER_DATA_FS, on_setattr=_set_lib_fs )
	lib_fs: FS = field( default=USER_DATA_FS )

	# database / fs
	_db: ActivityDb = field( default=None, alias='_db' )
	_db_fs: FS = field( default=None, alias='_db_fs' )

	# additional FS
	_root_fs: FS = field( default=OSFS( root_path='/', expand_vars=True ), alias='_root_fs' )
	_overlay_fs: FS = field( default=None, alias='_overlay_fs' )
	_takeouts_fs: FS = field( default=None, alias='_takeout_fs' )
	_log_fs: FS = field( default=None, alias='_log_fs' )
	_var_fs: FS = field( default=None, alias='_var_fs' )
	_backup_fs: FS = field( default=None, alias='_backup_fs' )
	_cache_fs: FS = field( default=None, alias='_cache_fs' )
	_tmp_fs: FS = field( default=None, alias='_tmp_fs' )
	_imports_fs: FS = field( default=None, alias='_imports_fs' )

	# plugin manager, registry, service manager
	plugin_mgr: Optional[PluginManager] = field( default=None )
	log_mgr: Optional[LogManager] = field( default=LogManager.instance() )
	registry: Optional[Registry] = field( default=None )
	service_mgr: Optional[ServiceManager] = field( default=None )
	parser: Optional[RuleParser] = field( default=None )

	# internal fields

	_cli_args: Tuple[Any, ...] = field( default=(), alias='_cli_args' )
	_cli_kwargs: Dict[str, Any] = field( factory=dict, alias='_cli_kwargs' )

	_init_with: Dict[str, Any] = field( factory=dict, alias='_init_with' )
	_config_dir: str = field( default=USER_CONFIG_FS.getsyspath( '/' ), alias='_config_dir' )
	_config_file: str = field( default=CONFIG_FILENAME, alias='_config_file' )

	def _load_configuration( self ):
		settings_files = [ f'{INSTALL_PATH}/{DEFAULT_CONFIG_FILENAME}' ]
		appstate_files = [ f'{INSTALL_PATH}/{DEFAULT_STATE_FILENAME}' ]

		try:
			settings_files.append( self.config_fs.getsyspath( CONFIG_FILENAME ) )
		except (ResourceNotFound, NoSysPath):
			# only for testing: config fs might be a multi fs with test data in underlay
			# therefore use the underlay fs to read configuration data
			# todo: check if this code can be removed in favour of a better solution, don't want test-specific code in here
			try:
				underlay = self.config_fs.get_fs( 'underlay' )
				settings_files.append( underlay.getsyspath( CONFIG_FILENAME ) )
				log.info( f'using configuration file found in FS {fs_to_str( underlay )}' )
			except AttributeError:
				pass
			log.warning( f'no configuration file found in FS {fs_to_str( self.config_fs )}' )

		# same procedure for state file
		try:
			appstate_files.append( self.config_fs.getsyspath( STATE_FILENAME ) )
		except (ResourceNotFound, NoSysPath):
			try:
				underlay = self.config_fs.get_fs( 'underlay' )
				appstate_files.append( underlay.getsyspath( STATE_FILENAME ) )
				log.info( f'using state file found in FS {fs_to_str( underlay )}' )
			except AttributeError:
				pass
			log.warning( f'no appstate file found in FS {fs_to_str( self.config_fs )}' )

		self.config = Configuration( settings_files=settings_files, merge_enabled=True )
		self.state = Configuration( settings_files=appstate_files, merge_enabled=True )

	def _setup_aux_fs( self, config_fs: Optional[FS] = None, lib_fs: Optional[FS] = None ) -> None:
		if config_fs:
			# relative to config fs
			self._takeouts_fs = _subfs( config_fs, TAKEOUT_DIRNAME )
			self._log_fs = _subfs( config_fs, LOG_DIRNAME )
			self._var_fs = _subfs( config_fs, VAR_DIRNAME )
			self._backup_fs = _subfs( config_fs, BACKUP_DIRNAME )
			self._cache_fs = _subfs( config_fs, CACHE_DIRNAME )
			self._tmp_fs = _subfs( self.var_fs, TMP_DIRNAME )
			self._imports_fs = _subfs( self.var_fs, IMPORT_DIRNAME )

		if lib_fs:
			# relative to lib fs
			self._db_fs = _subfs( lib_fs, DB_DIRNAME )
			self._overlay_fs = _subfs( lib_fs, OVERLAY_DIRNAME )

	def __attrs_post_init__( self ):
		# load config/appstate from factory locations + environment variables
		self._load_default_config()

		# update log manager to reflect configuration provided via environment variables
		self.log_mgr.set_console_log( self.config.verbose, self.config.debug, self.config.json )

		# used only for testing
		if self._init_with:
			self.apply_config( **self._init_with )

		return

		# create config fs
		log.debug( f'config/library FS configured to {fs_to_str( self.config_fs )} / {fs_to_str( self.lib_fs )}' )

		# setup auxillary fs which depend on config + lib fs
		self._setup_aux_fs( self.config_fs, self.lib_fs )

		# load configuration/appstate + apply command line args to configuration
		if cli_config := self._cli_kwargs.pop( KEY_CONFIGURATION, None ):
			self.config_fs = cli_config
		self._load_configuration()
		self.config.apply_config( { k: v for k, v in self._cli_kwargs.items() if v is not None } )

		# apply library configuration + load library (actually there's nothing to load yet)
		if self.config.library is not None:
			self.lib_fs = self.config.library

	def _load_default_config( self ) -> None:
		self.config = Configuration(
			settings_files=[ f'{INSTALL_PATH}/{DEFAULT_CONFIG_FILENAME}' ],
			merge_enabled=True,
			envvar_prefix=APP_PKG_NAME.upper(),
			load_dotenv=False,
			environments=False,
		)
		self.state = Configuration(
			settings_files=[ f'{INSTALL_PATH}/{DEFAULT_STATE_FILENAME}' ],
			merge_enabled=True,
			load_dotenv = False,
			environments = False,
		)

	def _load_user_config( self, configuration: Optional[str] = None ) -> None:
		if configuration:
			# attempt to load user-defined configuration file resp. from dir
			if self.root_fs.exists( configuration ) and self.root_fs.isdir( configuration ):
				configuration = self.root_fs.getsyspath( f'{configuration}/{CONFIG_FILENAME}' )
			self.config.load_file( configuration )

			# load appstate
			appstate = self.root_fs.getsyspath( f'{dirname( configuration )}/{STATE_FILENAME}' )
			self.appstate.load_file( appstate )

		else:
			# load from default configuration area
			self.config.load_file( self.config_fs.getsyspath( CONFIG_FILENAME ) )
			self.appstate.load_file( self.config_fs.getsyspath( STATE_FILENAME ) )

	def _create_config_fs( self, configuration: Optional[str] = None ) -> None:

		# create config_fs, lib_fs and auxillary folders
		if configuration:
			# reconfigure config_fs if provided via parameter
			config_dir = dirname( configuration ) if configuration.endswith('.yaml') else configuration
			self.config_fs = OSFS( config_dir, create=True, expand_vars=True )
			# self.lib_fs = OSFS( config_dir, create=True, expand_vars=True ) # put library inside config dir if provided?
		else:
			pass

		# create dependent FS objects
		self._takeouts_fs = _subfs( self.config_fs, TAKEOUT_DIRNAME )
		self._log_fs = _subfs( self.config_fs, LOG_DIRNAME )
		self._backup_fs = _subfs( self.config_fs, BACKUP_DIRNAME )
		self._cache_fs = _subfs( self.config_fs, CACHE_DIRNAME )

		self._var_fs = _subfs( self.config_fs, VAR_DIRNAME )
		self._tmp_fs = _subfs( self.var_fs, TMP_DIRNAME )
		self._imports_fs = _subfs( self.var_fs, IMPORT_DIRNAME )

	def _create_lib_fs( self, library: Optional[str] = None ) -> None:
		# use library from config if provided
		if library:
			self.lib_fs = OSFS( library, create=True, expand_vars=True )
		else:
			self.lib_fs = self.config_fs # use config directory as library as default ? or user data?

		# create dependent FS objects
		self._db_fs = _subfs( self.lib_fs, DB_DIRNAME )
		self._overlay_fs = _subfs( self.lib_fs, OVERLAY_DIRNAME )

	def apply_config( self, configuration: Optional[str] = None, library: Optional[str] = None,
	                  verbose: Optional[bool] = None, debug: Optional[bool] = None, force: Optional[bool] = None,
	                  pretend: Optional[bool] = None, json: Optional[bool] = None, ) -> None:

		# load user config
		self._load_user_config( configuration )

		# update configuration with command line args
		self.config.update(
			{ k: v for k, v in { 'verbose': verbose, 'debug': debug, 'force': force, 'pretend': pretend, 'json': json, 'library': library }.items() if v is not None }
		)

		# update log manager with merged config values
		self.log_mgr.set_console_log( self.config.verbose, self.config.debug, self.config.json )

		# create internally used FS objects
		self._create_config_fs( configuration )

		# create library fs
		self._create_lib_fs( library )

		# report how things are finally configured
		log.debug( f'using configuration area in {self.config_fs}' )
		log.debug( f'using library data in {self.lib_fs}' )

	# check if initialization was done

	@property
	def initialized( self ) -> bool:
		return self.config_fs and self.lib_fs

	# main properties

	@property
	def cfg( self ) -> Configuration:
		"""
		Alias for self.config

		:return: configuration object
		"""
		return self.config

	@property
	def settings( self ) -> Configuration:
		"""
		Alias for self.config

		:return: configuration object
		"""
		return self.config

	@property
	def appstate( self ) -> Configuration:
		"""
		Alias for self.state

		:return: configuration object
		"""
		return self.state

	@property
	def debug( self ) -> bool:
		return self.config.debug

	@property
	def verbose( self ) -> bool:
		return self.config.verbose

	@property
	def pretend( self ) -> bool:
		return self.config.pretend

	@property
	def force( self ) -> bool:
		return self.config.force

	@property
	def json( self ) -> bool:
		return self.config.json

	# root fs, for convenience
	@property
	def root_fs( self ) -> FS:
		return self._root_fs

	# lib/config related properties

	@property
	def config_dir( self ) -> str:
		return self.config_fs.getsyspath( '' )

	@property
	def config_file( self ) -> str:
		return self.config_fs.getsyspath( CONFIG_FILENAME )

	@property
	def state_file( self ) -> str:
		return self.config_fs.getsyspath( STATE_FILENAME )

	@property
	def lib_dir( self ) -> str:
		return self.lib_fs.getsyspath( '' )

	@property
	def lib_dir_path( self ) -> Path:
		return Path( self.lib_dir )

	@property
	def config_file_path( self ) -> Path:
		return Path( self.config_file )

	@property
	def state_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( STATE_FILENAME ) )

	# db related fs/dirs

	@property
	def db( self ) -> ActivityDb:
		return self._db

	@property
	def db_fs( self ) -> FS:
		return self._db_fs

	@property
	def db_dir( self ) -> str:
		return self.db_fs.getsyspath( '/' )

	@property
	def db_dir_path( self ) -> Path:
		return Path( self.db_dir )

	def db_fs_for( self, name: str ) -> FS:
		try:
			return OSFS( root_path=self.db_fs.getsyspath( name ), create=True )
		except (AttributeError, NoSysPath):
			return SubFS( self.db_fs, f'/{name}' )

	def plugin_fs( self, name: Optional[str] = None, user: Optional[str] = None, slug: Optional[str] = None ) -> MultiFS:
		if slug: # slug wins over name/user
			fs_path = slug
		else:
			fs_path = f'{name}/{user}' if user else name

		fs = MultiFS()
		fs.add_fs( name=OVERLAY_DIRNAME, fs=self.overlay_fs_for( fs_path ), write=False )
		fs.add_fs( name=DB_DIRNAME, fs=self.db_fs_for( fs_path ), write=True )
		return fs

	def plugin_dir( self, name: str, user: Optional[str], slug: Optional[str] ) -> str:
		return cast( MultiFS, self.plugin_fs( name, user, slug ) ).get_fs( DB_DIRNAME ).getsyspath( '' )

	def plugin_dir_path( self, name, user: Optional[str], slug: Optional[str] ) -> Path:
		return Path( self.plugin_dir( name, user, slug ) )

	# overlay

	@property
	def overlay_fs( self ) -> FS:
		return self._overlay_fs

	@property
	def overlay_dir( self ) -> str:
		return self.overlay_fs.getsyspath( '' )

	def overlay_fs_for( self, name: str ) -> FS:
		try:
			return OSFS( root_path=self.overlay_fs.getsyspath( name ), create=True )
		except (AttributeError, NoSysPath):
			return SubFS( self.overlay_fs, f'/{name}' )

	@property
	def db_overlay_path( self ) -> Path:
		return Path( self.overlay_dir )

	# takeouts

	@property
	def takeouts_fs( self ) -> FS:
		return self._takeouts_fs

	@property
	def takeouts_dir( self ) -> str:
		return self.takeouts_fs.getsyspath( '/' )

	@property
	def takeouts_dir_path( self ) -> Path:
		return Path( self.takeouts_dir )

	def takeout_fs_for( self, name: str ) -> FS:
		try:
			return OSFS( root_path=self.takeouts_fs.getsyspath( name ), create=True )
		except (AttributeError, NoSysPath, ResourceNotFound):
			return SubFS( self.takeouts_fs, f'/{name}' )

	def takeout_fs( self, name: Optional[str] = None, user: Optional[str] = None, slug: Optional[str] = None ) -> FS:
		if slug: # slug wins over name/user
			fs_path = slug
		else:
			fs_path = f'{name}/{user}' if user else name

		return self.takeout_fs_for( fs_path )

	def takeout_dir( self, name: str ) -> str:
		return self.takeout_fs( name ).getsyspath( '' )

	def takeout_dir_path( self, name ) -> Path:
		return Path( self.takeout_dir( name ) )

	# var/log/etc.

	@property
	def log_fs( self ) -> FS:
		return self._log_fs

	@property
	def log_dir( self ) -> str:
		return self.log_fs.getsyspath( '' )

	@property
	def log_file( self ) -> str:
		return self.log_fs.getsyspath( LOG_FILENAME )

	@property
	def log_file_path( self ) -> Path:
		return Path( self.log_file )

	# var

	@property
	def var_fs( self ) -> FS:
		return self._var_fs

	@property
	def var_dir( self ) -> str:
		return self.var_fs.getsyspath( '' )

	@property
	def var_path( self ) -> Path:
		return Path( self.var_dir )

	# tmp

	@property
	def tmp_fs( self ) -> FS:
		return self._tmp_fs

	# imports

	@property
	def imports_fs( self ) -> FS:
		return self._imports_fs

	@property
	def imports_dir( self ) -> str:
		return self.imports_fs.getsyspath( '' )

	@property
	def imports_path( self ) -> Path:
		return Path( self.imports_dir )

	def import_fs( self ) -> FS:
		return self.imports_fs.makedirs( f'{datetime.now( tz=tzlocal() ).strftime( "%y%m%d_%H%M%S" )}', recreate=True )

	# backup

	@property
	def backup_fs( self ) -> FS:
		return self._backup_fs

	@property
	def backup_dir( self ) -> str:
		return self.backup_fs.getsyspath( '' )

	@property
	def backup_path( self ) -> Path:
		return Path( self.backup_dir )

	# plugin configuration helpers

	def plugin_config_state( self, name, as_dict: bool = False ) -> Tuple[DynaBox, DynaBox]:
		name = name.lower()
		try:
			cfg = self.config.plugins[name] or DynaBox()
		except BoxKeyError:
			log.error( f'unable to find configuration area for plugin {name}' )
			cfg = DynaBox()

		try:
			state = self.state.plugins[name] or DynaBox()
		except BoxKeyError:
			log.error( f'unable to find app state area for plugin {name}' )
			state = DynaBox()

		return cfg, state

	def dump_config_state( self ) -> None:
		self.dump_config()
		self.dump_state()

	def dump_config( self ) -> None:
		self._dump_settings( self.config, CONFIG_FILENAME )

	def dump_state( self ) -> None:
		self._dump_settings( self.state, STATE_FILENAME )

	def _dump_settings( self, settings: Configuration, filename: str ):
		s = safe_dump( self._lower_dict( settings.as_dict() ), sort_keys=True, allow_unicode=True )
		self.config_fs.writetext( filename, s )

	def _lower_dict( self, d: Dict ) -> Dict:
		for k, v in d.copy().items():
			if isinstance( v, dict ):
				d.pop( k )
				d[f'{k.lower()}'] = v
				self._lower_dict( v )
			else:
				d.pop( k )
				d[f'{k.lower()}'] = v
		return d

# convenience helper

def _subfs( parent: FS, path: str ) -> SubFS:
	parent.makedirs( path, recreate=True )
	return SubFS( parent_fs=parent, path=path )

# global application context

CURRENT_CONTEXT: Optional[ApplicationContext] = None

def current_ctx() -> ApplicationContext:
	"""
	Returns the currently active context.

	:return: active application context
	"""
	global CURRENT_CONTEXT
	return CURRENT_CONTEXT

def set_current_ctx( ctx: ApplicationContext ) -> ApplicationContext:
	"""
	Sets the current application context.

	:param ctx: context to set
	:return: current context, for convenience
	"""
	global CURRENT_CONTEXT
	CURRENT_CONTEXT = ctx if ctx else CURRENT_CONTEXT
	return CURRENT_CONTEXT

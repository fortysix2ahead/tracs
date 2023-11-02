
from __future__ import annotations

from datetime import datetime
from importlib import import_module
from importlib.resources import path as pkg_path
from logging import getLogger
from os.path import join as os_path_join
from pathlib import Path
from pkgutil import extend_path, iter_modules
from typing import Any, Dict, List, Optional, Tuple

from attrs import define, field
from confuse import ConfigReadError, ConfigSource, Configuration, DEFAULT_FILENAME as DEFAULT_CFG_FILENAME, find_package_path, NotFoundError, YamlSource
from fs.base import FS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.path import abspath, basename, dirname, normpath
from platformdirs import user_config_dir
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# string constants

APPNAME = 'tracs'
APP_PKG_NAME = 'tracs'
PLUGINS_PKG_NAME = 'plugins'

BACKUP_DIRNAME = 'backup'
CACHE_DIRNAME = 'cache'
DB_DIRNAME = 'db'
DB_FILENAME = 'db.json'
LOG_DIRNAME = 'logs'
LOG_FILENAME = f'{APPNAME}.log'
OVERLAY_DIRNAME = 'overlay'
RESOURCES_DIRNAME = 'resources'
TAKEOUT_DIRNAME = 'takeouts'
TMP_DIRNAME = 'tmp'
VAR_DIRNAME = 'var'

CONFIG_FILENAME = 'config.yaml'
STATE_FILENAME = 'state.yaml'
DEFAULT_STATE_FILENAME = 'state_default.yaml'

DEFAULT_CFG_DIR = Path( user_config_dir( APPNAME ) )
DEFAULT_DB_DIR = Path( DEFAULT_CFG_DIR, DB_DIRNAME )

TABLE_NAME_DEFAULT = '_default'
TABLE_NAME_ACTIVITIES = 'activities'

CLASSIFIER = 'classifier'
CLASSIFIERS = 'classifiers'

KEY_CLASSIFER = 'classifier'
KEY_GROUP = 'group'
KEY_GROUPS = 'groups'
KEY_LAST_DOWNLOAD = 'last_download'
KEY_LAST_FETCH = 'last_fetch'
KEY_METADATA = 'metadata'
KEY_PARTS = 'parts'
KEY_PLUGINS = 'plugins'
KEY_SERVICE = KEY_CLASSIFER
KEY_RAW = 'raw'
KEY_RESOURCES = 'resources'
KEY_VERSION = 'version'

NAMESPACE_BASE = APPNAME
NAMESPACE_CONFIG = f'{NAMESPACE_BASE}.config'
NAMESPACE_PLUGINS = f'{NAMESPACE_BASE}.plugins'
NAMESPACE_SERVICES = f'{NAMESPACE_BASE}.services'

# default logger + console
log = getLogger( __name__ )

# one´console, reuse this in application context -> this needs to be consolidated
CONSOLE = Console( tab_size=2 )
console = CONSOLE
cs = CONSOLE

def default_plugin_path() -> Path:
	with pkg_path( APP_PKG_NAME, f'{PLUGINS_PKG_NAME}/__init__.py' ) as path:
		return path

def default_resources_path() -> Path:
	with pkg_path( APP_PKG_NAME, f'{RESOURCES_DIRNAME}' ) as path:
		return path

# application context

@define( init=False )
class ApplicationContext:

	config: Configuration = field( default=None )

	# configuration + library are absolute paths, library points to configuration by default
	configuration: str = field( default=None )
	library: str = field( default=None )

	# global configuration flags, can be set externally
	force: Optional[bool] = field( default=None )
	verbose: Optional[bool] = field( default=None )
	debug: Optional[bool] = field( default=None )
	pretend: Optional[bool] = field( default=None )

	# everything below here is calculated and will be set up in post_init

	# filesystems
	config_fs: Optional[FS] = field( default=None )
	lib_fs: Optional[FS] = field( default=None )

	# config/state files
	config_file: str = field( default=CONFIG_FILENAME )
	state_file: str = field( default=STATE_FILENAME )

	log_dir: str = field( default=LOG_DIRNAME )
	log_file: str = field( default=os_path_join( LOG_DIRNAME, LOG_FILENAME ) )
	overlay_dir: str = field( default=OVERLAY_DIRNAME )
	takeout_dir: str = field( default=TAKEOUT_DIRNAME )
	var_dir: str = field( default=VAR_DIRNAME )
	backup_dir: str = field( default=os_path_join( VAR_DIRNAME, BACKUP_DIRNAME ) )
	cache_dir: str = field( default=os_path_join( VAR_DIRNAME, CACHE_DIRNAME ) )
	tmp_dir: str = field( default=os_path_join( VAR_DIRNAME, TMP_DIRNAME ) )

	# database
	db: Any = field( default=None )
	db_dir: str = field( default=DB_DIRNAME )

	instance: Any = field( default=None )

	# app configuration + state
	state: Configuration = field( default=None )
	meta: Any = field( default=None ) # not used yet

	# plugins
	plugins: Dict[str, Any] = field( factory=dict )
	plugin_fs: FS = field( factory=MultiFS )
	plugins_dir: List[Path] = field( factory=list )

	# todo: remove the console from here
	console: Console = field( default=CONSOLE )
	progress: Progress = field( default=None )
	task_id: Any = field( default=None )

	# internal fields

	__kwargs__: Dict[str, Any] = field( factory=dict, alias='__kwargs__' )
	apptime: datetime = field( default=None )

	def __setup_configuration__( self ):
		# create configuration -> this reads the default config files automatically
		self.config = Configuration( APPNAME, APP_PKG_NAME )

		# read default plugin configuration
		plugins_pkg_path = find_package_path( f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}' )
		self.config.set_file( f'{plugins_pkg_path}/{DEFAULT_CFG_FILENAME}' )

		if not self.configuration:
			self.configuration = user_config_dir( APPNAME )

		# add user configuration file provided via -c option
		try:
			user_configuration = self.__kwargs__.pop( 'configuration' )
			# todo: is it possible to expand relative paths without creating a FS?
			fs = OSFS( root_path=dirname( user_configuration ), expand_vars=True )
			user_configuration = fs.getsyspath( basename( user_configuration ) )
			self.configuration = dirname( user_configuration )
			self.config.set_file( user_configuration, base_for_paths=True )
		except (AttributeError, KeyError):
			# self.configuration = self.config.config_dir() # this returns ~/.config/tracs on Mac OS X -> wrong
			self.configuration = user_config_dir( APPNAME )
		except ConfigReadError:
			# noinspection PyUnboundLocalVariable
			log.error( f'error reading configuration from {user_configuration}' )
		finally:
			self.config_fs = OSFS( root_path=self.configuration, create=True )

		# add configuration from command line arguments
		# todo: there might be other kwargs apart from config-related -> remove first
		kwargs = { k: v for k, v in self.__kwargs__.items() if v is not None and v != '' and k != 'db' }
		self.config.set( kwargs )

	def __setup_state__( self ):
		self.state = Configuration( APPNAME, APP_PKG_NAME, read=False )

		app_pkg_path = find_package_path( APP_PKG_NAME )
		plugins_pkg_path = find_package_path( f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}' )

		# default state
		self.state.set_file( f'{app_pkg_path}/{DEFAULT_STATE_FILENAME}' )

		# plugin state
		self.state.set_file( f'{plugins_pkg_path}/{DEFAULT_STATE_FILENAME}' )

		# user state
		try:
			self.state.set_file( f'{self.configuration}/{STATE_FILENAME}', base_for_paths=True )
		except ConfigReadError:
			log.error( f'error reading application state from {self.configuration}/{STATE_FILENAME}' )

		self.state.read( user=False, defaults=False )

	def __setup_library__( self ):
		try:
			self.library = self.config['library'].get()
		except NotFoundError:
			pass
		finally:
			if self.library is None:
				self.library = self.configuration
			self.lib_fs = OSFS( root_path=self.library, create=True )

	def __create_default_directories__( self ):
		# create directories depending on config_dir
		self.config_fs.makedir( self.log_dir, recreate=True )

		# create directories depending on lib_dir
		self.lib_fs.makedir( self.db_dir, recreate=True )
		self.lib_fs.makedir( self.overlay_dir, recreate=True )
		self.lib_fs.makedir( self.takeout_dir, recreate=True )

		# var and its children
		self.lib_fs.makedir( self.var_dir, recreate=True )
		self.lib_fs.makedir( self.backup_dir, recreate=True )
		self.lib_fs.makedir( self.cache_dir, recreate=True )
		self.lib_fs.makedir( self.tmp_dir, recreate=True )

	def __setup_plugins__( self ):
		# noinspection PyUnresolvedReferences
		import tracs.plugins

		try:
			pluginpath = (self.config['pluginpath'].get() or '').split( ' ' )
			for pp in pluginpath:
				plugin_path = OSFS( root_path=pp, expand_vars=True ).getsyspath( '/tracs/plugins' )
				tracs.plugins.__path__ = extend_path( [plugin_path], 'tracs.plugins' )
		except NotFoundError:
			log.error( 'error loading value from configuration key pluginpath' )

		for finder, name, ispkg in iter_modules( tracs.plugins.__path__ ):
			self.plugins[f'{name}'] = import_module( f'tracs.plugins.{name}' )
			log.debug( f'imported plugin {name} from {finder.path}' )

	def __init__( self, *args, **kwargs ):
		# noinspection PyUnresolvedReferences
		self.__attrs_init__( *args, **kwargs, __kwargs__={ **kwargs } )

	def __attrs_post_init__( self ):
		self.__setup_configuration__()
		self.__setup_state__()

		# update global options fields from config -> todo: this should be removed in the future, access should be like cfg.debug
		self.debug = self.config['debug'].get()
		self.verbose = self.config['verbose'].get()
		self.force = self.config['force'].get()
		self.pretend = self.config['pretend'].get()

		self.__setup_library__()

		self.__create_default_directories__()

		# load/manage plugins
		self.__setup_plugins__()

	@property
	def config_dir( self ) -> str:
		return self.configuration

	@property
	def lib_dir( self ) -> str:
		return self.library

	@property
	def config_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( str( self.config_file ) ) )

	@property
	def state_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( str( self.state_file ) ) )

	@property
	def db_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( str( self.db_dir ) ) )

	@property
	def db_dir_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( str( self.db_dir ) ) )

	@property
	def db_overlay_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( str( self.overlay_dir ) ) )

	@property
	def lib_dir_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( '/' ) )

	@property
	def log_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( str( self.log_file ) ) )

	@property
	def var_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( '/' ), self.var_dir )

	@property
	def backup_path( self ) -> Path:
		return Path( self.lib_fs.getsyspath( '/' ), self.backup_dir )

	# path helpers

	def db_dir_for( self, service_name: str ) -> Path:
		return Path( self.db_dir_path, service_name )

	def takeouts_dir_for( self, service_name: str ) -> Path:
		return Path( self.lib_dir, self.takeout_dir, service_name )

	def pp( self, *objects ):
		self.console.print( *objects )

	def ppx( self ):
		self.console.print_exception()

	def start( self, description: str = '', total = None ):
		if self.verbose:
			if description:
				self.pp( description )
		else:
			# create progress and start as start/stop/reuse does not seem to work
			columns = [
				TextColumn( '[progress.description]{task.description}' ),
				BarColumn(),
				TaskProgressColumn(),
				TimeElapsedColumn(),
				TextColumn( '/' ),
				TimeRemainingColumn(),
				TextColumn( '[cyan]to go[/cyan]' ),
				TextColumn( '{task.fields[msg]}' )
			]
			self.progress = Progress( *columns, console=self.console )
			self.progress.start()
			self.task_id = self.progress.add_task( description=description, total=total, msg='' )

	def total( self, total=None ):
		if self.progress is None:
			self.start( total=total )
		else:
			self.progress.update( task_id=self.task_id, total=total )

	def advance( self, msg: str = None, advance: float = 1 ):
		if self.verbose:
			self.pp( msg )
		else:
			if not self.progress: # todo: improve, this might happen during testing strava ...
				return

			self.progress.update( task_id=self.task_id, advance=advance, msg=msg )

	def complete( self, msg: str = None ):
		if self.verbose:
			if msg:
				self.pp( msg )
		else:
			if not self.progress: # todo: improve, this might happen during testing strava ...
				return

			self.progress.update( task_id=self.task_id, advance=1, msg='' if msg is None else msg )
			self.progress.stop()

	def timeit( self, message: Optional[str] = None, skip_print: bool = False ):
		if not self.apptime:
			self.apptime = datetime.now()
		else:
			diff = datetime.now() - self.apptime
			if not skip_print:
				if message:
					self.console.print(f'{message}: {diff}')
				else:
					self.console.print( f'{diff}' )
			self.apptime = datetime.now()

	# plugin configuration helpers

	def plugin_config_state( self, name, as_dict: bool = False ) -> Tuple:
		name = name.lower()
		cfg, state = self.config['plugins'][name], self.state['plugins'][name]
		if as_dict:
			try:
				cfg = cfg.get()
			except NotFoundError:
				cfg = dict()

			try:
				state = state.get()
			except NotFoundError:
				cfg = dict()

		return cfg, state

	def plugin_config( self, plugin_name ) -> Dict:
		if not self.config['plugins'][plugin_name].get():
			self.config['plugins'][plugin_name] = {}
		return self.config['plugins'][plugin_name].get()

	def plugin_state( self, plugin_name ) -> Dict:
		if not self.state['plugins'][plugin_name].get():
			self.state['plugins'][plugin_name] = {}
		return self.state['plugins'][plugin_name].get()

	def dump_config_state( self ) -> None:
		self.dump_config()
		self.dump_state()

	def dump_config( self ) -> None:
		self.config_fs.writetext( CONFIG_FILENAME, self.config.dump( full=True ) )

	def dump_state( self ) -> None:
		self.config_fs.writetext( STATE_FILENAME, self.state.dump( full=True ) )

ApplicationConfig = Configuration( APPNAME, __name__, read=False )
ApplicationState = Configuration( f'{APPNAME}-state', __name__, read=False )


from __future__ import annotations

from datetime import datetime
from importlib import import_module
from importlib.resources import path as pkg_path
from logging import getLogger
from pathlib import Path
from pkgutil import extend_path, iter_modules
from typing import Any, cast, Dict, Optional, Tuple

from attrs import define, field
from confuse import ConfigReadError, Configuration, find_package_path, NotFoundError
from fs.base import FS
from fs.errors import NoSysPath
from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.path import dirname
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
DEFAULT_CONFIG_FILENAME = 'config_default.yaml'
DEFAULT_STATE_FILENAME = 'state_default.yaml'

EXTRA_KWARGS = ['debug', 'force', 'verbose', 'pretend']

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

	# config/state files / fs
	config: Configuration = field( default=None )
	config_dir: str = field( default=None )
	config_file: str = field( default=None )
	state_file: str = field( default=None )
	config_fs: FS = field( default=None )

	# library fs
	lib_dir: str = field( default=None )
	lib_fs: FS = field( default=None )

	# database / fs
	db: Any = field( default=None )
	db_fs: FS = field( default=None )
	overlay_fs: FS = field( default=None )

	# takeouts
	takeouts_fs: FS = field( default=None )

	# logs
	log_fs: FS = field( default=None )
	var_fs: FS = field( default=None )
	backup_fs: FS = field( default=None )
	cache_fs: FS = field( default=None )
	tmp_fs: FS = field( default=None )

	# needed?
	instance: Any = field( default=None )

	# app configuration + state
	state: Configuration = field( default=None )
	meta: Any = field( default=None ) # not used yet

	# plugins
	plugins: Dict[str, Any] = field( factory=dict )

	# kwargs fields, not used, but needed for

	# todo: move this stuff away, as it does not belong here
	console: Console = field( default=CONSOLE )
	progress: Progress = field( default=None )
	task_id: Any = field( default=None )

	# internal fields

	__kwargs__: Dict[str, Any] = field( factory=dict, alias='__kwargs__' )
	__init_fs__: bool = field( default=True, alias='__init_fs__' )
	__apptime__: datetime = field( default=datetime.utcnow(), alias='__apptime__' )

	apptime: datetime = field( default=None )

	def __setup_config_fs__( self ):
		if self.config_file:
			self.config_fs = OSFS( root_path=dirname( self.config_file ), expand_vars=True )
		elif self.config_dir:
			self.config_fs = OSFS( root_path=self.config_dir, expand_vars=True )

		if not self.config_fs:
			self.config_fs = OSFS( root_path=user_config_dir( APPNAME ) )

		try:
			self.config_dir = self.config_fs.getsyspath( '/' )
			self.config_file = self.config_fs.getsyspath( f'/{CONFIG_FILENAME}' )
		except NoSysPath:
			pass

	def __setup_configuration__( self ):
		# create configuration -> this reads the default config files automatically
		self.config = Configuration( APPNAME, APP_PKG_NAME )

		# read default plugin configuration
		plugins_pkg_path = find_package_path( f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}' )
		self.config.set_file( f'{plugins_pkg_path}/{DEFAULT_CONFIG_FILENAME}' )

		# add user configuration file provided via -c option
		try:
			self.config.set_file( self.config_fs.getsyspath( CONFIG_FILENAME ), base_for_paths=True )
		except (AttributeError, KeyError, TypeError):
			pass
		except (ConfigReadError, NoSysPath):
			log.error( f'error reading configuration from {self.config_fs}' )

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
			self.state_file = self.config_fs.getsyspath( f'/{STATE_FILENAME}' )
			self.state.set_file( self.state_file, base_for_paths=True )
		except (ConfigReadError, NoSysPath):
			log.error( f'error reading application state from {self.config_fs}' )

		self.state.read( user=False, defaults=False )

	def __setup_library__( self ):
		if self.lib_dir:
			library = self.lib_dir
		else:
			try:
				library = self.config['library'].get()
			except NotFoundError:
				library = self.config_dir

		if not library:
			library = self.config_dir

		try:
			self.lib_fs = OSFS( root_path=library, expand_vars=True, create=True )
			self.lib_dir = self.lib_fs.getsyspath( '' )
			self.db_fs = OSFS( root_path=f'{self.lib_fs.getsyspath( "" )}/{DB_DIRNAME}', create=True )
			self.overlay_fs = OSFS( root_path=f'{self.lib_fs.getsyspath( "" )}/{OVERLAY_DIRNAME}', create=True )
		except (NoSysPath, TypeError):
			pass

	def __setup_aux__( self ):
		try:
			# takeouts
			self.takeouts_fs = OSFS( root_path=self.config_fs.getsyspath( f'{TAKEOUT_DIRNAME}' ), create=True )

			# logs, var etc.
			self.log_fs = OSFS( root_path=self.config_fs.getsyspath( f'{LOG_DIRNAME}' ), create=True )
			self.var_fs = OSFS( root_path=self.config_fs.getsyspath( f'{VAR_DIRNAME}' ), create=True )
			self.backup_fs = OSFS( root_path=self.config_fs.getsyspath( f'{BACKUP_DIRNAME}' ), create=True )
			self.cache_fs = OSFS( root_path=self.config_fs.getsyspath( f'{CACHE_DIRNAME}' ), create=True )
			self.tmp_fs = OSFS( root_path=self.config_fs.getsyspath( f'{TMP_DIRNAME}' ), create=True )
		except (NoSysPath, TypeError):
			pass

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
			log.debug( f'importing plugin [bold green]{name}[/bold green] from {finder.path}' )
			self.plugins[f'{name}'] = import_module( f'tracs.plugins.{name}' )

	def __init__( self, *args, **kwargs ):
		extra_kwargs = { k: kwargs.pop( k, False ) for k in EXTRA_KWARGS }
		# noinspection PyUnresolvedReferences
		self.__attrs_init__( *args, **kwargs, __kwargs__ = extra_kwargs  )

	def __attrs_post_init__( self ):
		# create config fs
		self.__setup_config_fs__()

		# read configuration/state
		self.__setup_configuration__()
		self.__setup_state__()

		# set up library structure
		self.__setup_library__()

		# create default directories
		self.__setup_aux__()

		# load/manage plugins
		self.__setup_plugins__()

	# main properties

	@property
	def debug( self ) -> bool:
		return self.config['debug'].get()

	@property
	def verbose( self ) -> bool:
		return self.config['verbose'].get()

	@property
	def pretend( self ) -> bool:
		return self.config['pretend'].get()

	@property
	def force( self ) -> bool:
		return self.config['force'].get()

	# lib/config related properties

	@property
	def lib_dir_path( self ) -> Path:
		return Path( self.lib_dir )

	@property
	def config_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( CONFIG_FILENAME ) )

	@property
	def state_file_path( self ) -> Path:
		return Path( self.config_fs.getsyspath( STATE_FILENAME ) )

	# db related fs/dirs

	@property
	def db_dir( self ) -> str:
		return self.db_fs.getsyspath( '/' )

	@property
	def db_dir_path( self ) -> Path:
		return Path( self.db_dir )

	def db_fs_for( self, name: str ) -> FS:
		return OSFS( root_path=self.db_fs.getsyspath( name ), create=True )

	def plugin_fs( self, name: str ) -> FS:
		fs = MultiFS()
		fs.add_fs( name=OVERLAY_DIRNAME, fs=self.overlay_fs_for( name ), write=False )
		fs.add_fs( name=DB_DIRNAME, fs=self.db_fs_for( name ), write=True )
		return fs

	def plugin_dir( self, name: str ) -> str:
		return cast( MultiFS, self.plugin_fs( name ) ).get_fs( DB_DIRNAME ).getsyspath( '' )

	def plugin_dir_path( self, name ) -> Path:
		return Path( self.plugin_dir( name ) )

	@property
	def overlay_dir( self ) -> str:
		return self.overlay_fs.getsyspath( '' )

	def overlay_fs_for( self, name: str ) -> FS:
		return OSFS( root_path=self.overlay_fs.getsyspath( name ), create=True )

	@property
	def db_overlay_path( self ) -> Path:
		return Path( self.overlay_dir )

	# takeouts

	@property
	def takeouts_dir( self ) -> str:
		return self.takeouts_fs.getsyspath( '/' )

	@property
	def takeouts_dir_path( self ) -> Path:
		return Path( self.takeouts_dir )

	def takeout_fs( self, name: str ) -> FS:
		return OSFS( root_path=self.takeouts_fs.getsyspath( f'{name}' ), create=True )

	def takeout_dir( self, name: str ) -> str:
		return self.takeout_fs( name ).getsyspath( '' )

	def takeout_dir_path( self, name ) -> Path:
		return Path( self.takeout_dir( name ) )

	# var/log/etc.

	@property
	def log_dir( self ) -> str:
		return self.log_fs.getsyspath( '' )

	@property
	def log_file( self ) -> str:
		return self.log_fs.getsyspath( LOG_FILENAME )

	@property
	def log_file_path( self ) -> Path:
		return Path( self.log_file )

	@property
	def var_dir( self ) -> str:
		return self.var_fs.getsyspath( '' )

	@property
	def var_path( self ) -> Path:
		return Path( self.var_dir )

	@property
	def backup_dir( self ) -> str:
		return self.backup_fs.getsyspath( '' )

	@property
	def backup_path( self ) -> Path:
		return Path( self.backup_dir )

	# other helpers -> these need to be removed!

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

# convenience helper

CURRENT_CONTEXT: Optional[ApplicationContext] = None

def current_ctx() -> ApplicationContext:
	global CURRENT_CONTEXT
	return CURRENT_CONTEXT

def set_current_ctx( ctx: ApplicationContext ) -> None:
	global CURRENT_CONTEXT
	CURRENT_CONTEXT = ctx if ctx else CURRENT_CONTEXT

#

ApplicationConfig = Configuration( APPNAME, __name__, read=False )
ApplicationState = Configuration( f'{APPNAME}-state', __name__, read=False )

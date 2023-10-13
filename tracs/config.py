
from __future__ import annotations

from datetime import datetime
from importlib.resources import path as pkg_path
from logging import getLogger
from os.path import join as os_path_join
from pathlib import Path
from typing import Any, Dict, List, Optional

from appdirs import AppDirs
from attrs import define, field
from confuse import ConfigSource, Configuration, DEFAULT_FILENAME as DEFAULT_CFG_FILENAME, find_package_path, YamlSource
from fs.base import FS
from fs.osfs import OSFS
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# string constants

APPNAME = 'tracs'
APP_PKG_NAME = 'tracs'
PLUGINS_PKG_NAME = 'plugins'

APPDIRS = AppDirs( appname=APPNAME )

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

DEFAULT_CFG_DIR = Path( APPDIRS.user_config_dir )
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

def default_resources_path() -> Path:
	with pkg_path( APP_PKG_NAME, f'{RESOURCES_DIRNAME}' ) as path:
		return path

class ApplicationConfiguration( Configuration ):

	def __init__( self, config_file_path: Optional[str] = None, args: Dict = None ):
		self._arguments = args if args is not None else {}
		self._plugins_package_path = find_package_path( f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}' )
		self._config_file_path = config_file_path

		# call super().init
		super().__init__( appname=APPNAME, modname=APPNAME )

	def read( self, user=True, defaults=True ):
		self._add_arguments_source()
		self._add_user_source()
		self._add_plugins_default_source()
		self._add_default_source()

	def user_config_path( self ):
		return self._config_file_path if self._config_file_path else super().user_config_path()

	def _add_arguments_source( self ):
		self.add( ConfigSource.of( self._arguments ) )

	def _add_plugins_default_source( self ):
		filename = os_path_join( self._plugins_package_path, DEFAULT_CFG_FILENAME )
		self.add( YamlSource( filename, loader=self.loader, optional=True, default=True ) )

# similar to ApplicationConfiguration above, but slightly different

class ApplicationStateCls( Configuration ):

	def __init__( self, state_file_path: Optional[str] = None ):
		self._plugins_package_path = find_package_path( f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}' )
		self._state_file_path = state_file_path

		# call super().init
		super().__init__( appname=APPNAME, modname=APPNAME )

	def read( self, user=True, defaults=True ):
		self._add_user_source()
		self._add_plugins_default_source()
		self._add_default_source()

	def user_config_path( self ):
		return self._state_file_path if self._state_file_path else os_path_join( self.config_dir(), STATE_FILENAME )

	def _add_plugins_default_source( self ):
		filename = os_path_join( self._plugins_package_path, DEFAULT_STATE_FILENAME )
		self.add( YamlSource( filename, loader=self.loader, optional=True, default=True ) )

	def _add_default_source( self ):
		filename = os_path_join( self._package_path, DEFAULT_STATE_FILENAME )
		self.add( YamlSource( filename, loader=self.loader, optional=True, default=True ) )

# application context

@define
class ApplicationContext:

	# configuration fields which can be set externally

	# config + lib dir are absolute paths, lib_dir points to cfg_dir by default
	config_dir: str = field( default=APPDIRS.user_config_dir )
	lib_dir: str = field( default=APPDIRS.user_config_dir )

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
	config: Configuration = field( default=None )
	state: Configuration = field( default=None )
	meta: Any = field( default=None ) # not used yet

	plugins_dir: List[Path] = field( factory=list )

	console: Console = field( default=CONSOLE )
	progress: Progress = field( default=None )
	task_id: Any = field( default=None )

	apptime: datetime = field( default=None )

	def __attrs_post_init__( self ):
		# setup config fs
		self.config_dir = APPDIRS.user_config_dir if self.config_dir is None else self.config_dir # config dir may never be None
		self.config_fs = OSFS( root_path=self.config_dir, create=True )

		# load default configuration/state
		args = { k: v for k, v in {
			'debug': self.debug,
			'verbose': self.verbose,
			'force': self.force,
			'pretend': self.pretend,
			'library': self.lib_dir,
		}.items() if v is not None }
		self.config = ApplicationConfiguration( config_file_path=os_path_join( self.config_dir, self.config_file ), args = args )
		self.state = ApplicationStateCls( state_file_path=os_path_join( self.config_dir, self.state_file ) )

		# update global options fields from config -> todo: this should be removed in the future, access should be like cfg.debug
		self.debug = self.config['debug'].get( bool )
		self.verbose = self.config['verbose'].get( bool )
		self.force = self.config['force'].get( bool )
		self.pretend = self.config['pretend'].get( bool )

		# setup library fs
		if (library := self.config['library'].get()) is None:
			self.lib_dir = self.config_dir
		else:
			self.lib_dir = library

		self.lib_fs = OSFS( root_path=self.lib_dir, create=True )
		self.config['library'] = self.lib_dir

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

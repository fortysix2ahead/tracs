from __future__ import annotations

from logging import getLogger
from typing import ClassVar, Optional, Tuple

from attrs import define, field
from dynaconf import Dynaconf as Configuration

from tracs.__log__ import LogManager
from tracs.activity import Activity
from tracs.context import ApplicationContext
from tracs.core import augment
from tracs.db import ActivityDb
from tracs.pluginmgr import PluginManager, Registry, ServiceManager
from tracs.rules import RuleParser

log = getLogger( __name__ )

@define
class Application:

	_instance: ClassVar[Application|None] = None  # application singleton

	_ctx: ApplicationContext = field( default=None, alias='_ctx' )
	_log_manager: LogManager|None = field( default=LogManager.instance(), alias='_log_manager' )

	@classmethod
	def instance( cls, *args, **kwargs ):
		if cls._instance is None:
			cls._instance = Application( _log_manager=LogManager.instance() )
		return cls._instance

	def __attrs_post_init__( self ):
		self._ctx = ApplicationContext()
		self.ctx.plugin_mgr = PluginManager.instance()
		self.ctx.log_mgr = LogManager.instance()

	def init( self, configuration: Optional[str] = None, library: Optional[str] = None,
	          verbose: Optional[bool] = False, debug: Optional[bool] = False, force: Optional[bool] = False,
	          pretend: Optional[bool] = False, json: Optional[bool] = False, ) -> None:
		"""
		Initialize the application.
		This is supposed to be called after the CLI has been set up because the parameters may have been provided as
		CLI arguments.
		"""

		# update application context with user-defined configuration
		self.ctx.update( configuration=configuration, library=library, verbose=verbose, debug=debug, force=force, pretend=pretend, json=json )

		# file logging setup after configuration has been loaded --
#		LogManager.instance().set_file_log( self.ctx.config.verbose, self.ctx.config.debug, self.ctx.log_file_path )

		# print context configuration
		log.debug( f'using configuration from {self.ctx.config_dir} and library in {self.ctx.lib_dir}' )

		# setup plugin manager
		if self.ctx.config.plugins.paths:
			plugin_paths = self.ctx.config.plugins.paths.split() if isinstance( self.ctx.config.plugins.paths, str ) else self.ctx.config.plugins.paths
		else:
			plugin_paths = []
		if self.ctx.config.plugins.modules:
			modules = self.ctx.config.plugins.modules.split() if isinstance( self.ctx.config.plugins.modules, str ) else self.ctx.config.plugins.modules
		else:
			modules = []

		self.ctx.plugin_mgr.init( plugin_paths=plugin_paths, plugin_names=modules )
		self.ctx.registry = self.plugin_mgr.registry
		self.ctx.service_mgr = self.plugin_mgr.service_mgr

		# create rule parser
		self.ctx.parser = RuleParser( keywords=self.registry.keywords, normalizers=self.registry.normalizers )

		# augment Activity class with derived fields
		for df in self.registry.derived_fields:
			augment( Activity, df )

		# init service manager
		[self.service_mgr.add_class( s ) for s in self.registry.services ]
		for name, cfg in self.ctx.config.services.items():
			self.service_mgr.add_from( self.ctx, name, cfg )

		# init db from config_dir
		self.ctx._db = ActivityDb(
			path=self.ctx.db_dir_path,
			read_only=self.ctx.pretend,
			enable_index=self.ctx.config.db.index,
			summary_types=self.registry.summary_type_names(),
			recording_types=self.registry.recording_type_names()
		)

		# ---- register cleanup functions ----
#		register_atexit( self._ctx.db.close )
#		register_atexit( self._ctx.dump_state )

	# properties

	@property
	def ctx( self ) -> ApplicationContext:
		return self._ctx

	@property
	def db( self ) -> ActivityDb:
		return self.ctx.db

	@property
	def registry( self ) -> Optional[Registry]:
		return self.ctx.registry

	@property
	def plugin_mgr( self ) -> Optional[PluginManager]:
		return self.ctx.plugin_mgr

	@property
	def service_mgr( self ) -> Optional[ServiceManager]:
		return self.ctx.service_mgr

	@property
	def parser( self ) -> Optional[RuleParser]:
		return self.ctx.parser

	@property
	def config( self ) -> Configuration:
		return self.ctx.config

	@property
	def state( self ) -> Configuration:
		return self.ctx.state

	@property
	def as_tuple( self ) -> Tuple[ApplicationContext, ActivityDb]:
		return self.ctx, self.ctx.db

def _config_dir_file( configuration: Optional[str] ) -> Tuple[Optional[str], Optional[str]]:
	return None, None

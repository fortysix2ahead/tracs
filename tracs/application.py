from __future__ import annotations

from logging import getLogger
from typing import ClassVar, Optional, Tuple

from attrs import define, field
from dynaconf import Dynaconf as Configuration

from tracs.activity import Activity, configure_formatters as configure_activity_formatters
from tracs.context import ApplicationContext
from tracs.db import ActivityDb
from tracs.pluginmgr import PluginManager, Registry, ServiceManager
from tracs.rules import RuleParser
from tracs.utils import UCFG

log = getLogger( __name__ )

@define( init=False )
class Application:

	_instance: ClassVar[Application] = None  # application singleton

	_ctx: ApplicationContext = field( default=None, alias='_ctx' )

	_service_mgr: ServiceManager = field( default=None, alias='_service_mgr' )
	_db: ActivityDb = field( default=None, alias='_db' )
	_registry: Registry = field( default=None, alias='_registry' )
	_parser: RuleParser = field( default=None, alias='_parser' )

	@classmethod
	def instance( cls, *args, **kwargs ):
		if cls._instance is None:
			cls._instance = Application.__new__( cls, *args, **kwargs )
		return cls._instance

	# constructor
	def __init__( self ):
		raise RuntimeError( 'instance can only be created by using Application.instance( cls ) method' )

	@classmethod
	def __new__( cls, *args, **kwargs ):
		instance = super( Application, cls ).__new__( cls )
		instance.__setup__( *args, **kwargs )
		return instance

	# 'None' as default value means value has not been provided from the outside (via command line switch)
	def __setup__( self, *args, **kwargs ):
		# console logging setup --
		from tracs.__log__ import LogManager
		LogManager.instance().set_console_log( kwargs.get( 'verbose', False ), kwargs.get( 'debug', False ), kwargs.get( 'json', False ) )

		# log command line flags
		log.debug( f'parameters provided from command line: {kwargs}' )

		# create context, based on cfg_dir
		self._ctx = ApplicationContext( _cli_args=args, _cli_kwargs=kwargs )

		# file logging setup after configuration has been loaded --
		LogManager.instance().set_file_log( self._ctx.config.verbose, self._ctx.config.debug, self._ctx.log_file_path )

		# print context configuration
		log.debug( f'using configuration from {self._ctx.config_dir} and library in {self._ctx.lib_dir}' )

		# init plugin manager
		self._ctx.plugin_mgr = PluginManager.inst().init( (self._ctx.config.pluginpath or '').split( ' ' ) )
		self._ctx.service_mgr = self._ctx.plugin_mgr.service_mgr

		# init registry
		self._registry = PluginManager.inst().registry()
		self._ctx.registry = self._registry

		# init db from config_dir
		self._db = ActivityDb(
			path=self._ctx.db_dir_path,
			read_only=self._ctx.pretend,
			enable_index=self.ctx.config.db.index,
			summary_types=self.registry.summary_type_names(),
			recording_types=self.registry.recording_type_names()
		)
		self._ctx._db = self._db

		# create rule parser
		self._parser = RuleParser( keywords=self.registry.keywords, normalizers=self.registry.normalizers )
		self._ctx.parser = self._parser

		# announce virtual fields to activity class
		for vf in self.registry.virtual_fields:
			Activity.VF().add( vf )

		# init service manager
		for s in self.registry.services:
			self.service_mgr.add_class( s )
		for name, cfg in self._ctx.config.services.items():
			self.service_mgr.add_from( self._ctx, name, cfg )

		# ---- announce context/configuration to utils module + configure formatters ----
		UCFG.reconfigure( self._ctx.config )
		configure_activity_formatters( self._ctx.config.formats )

		# ---- register cleanup functions ----
#		register_atexit( self._ctx.db.close )
#		register_atexit( self._ctx.dump_state )

	# properties

	@property
	def ctx( self ) -> ApplicationContext:
		return self._ctx

	@property
	def db( self ) -> ActivityDb:
		return self._db

	@property
	def registry( self ) -> Registry:
		return self._registry

	@property
	def plugin_mgr( self ) -> PluginManager:
		return self._ctx.plugin_mgr

	@property
	def service_mgr( self ) -> ServiceManager:
		return self._ctx.service_mgr

	@property
	def parser( self ) -> RuleParser:
		return self._parser

	@property
	def config( self ) -> Configuration:
		return self._ctx.config

	@property
	def state( self ) -> Configuration:
		return self._ctx.state

	@property
	def as_tuple( self ) -> Tuple[ApplicationContext, ActivityDb]:
		return self.ctx, self.db

def _config_dir_file( configuration: Optional[str] ) -> Tuple[Optional[str], Optional[str]]:
	return None, None
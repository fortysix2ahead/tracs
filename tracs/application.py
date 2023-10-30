from __future__ import annotations

from atexit import register as register_atexit
from logging import getLogger
from typing import ClassVar

from attrs import define, field

from tracs import setup_console_logging, setup_file_logging
from .config import ApplicationContext
from .db import ActivityDb
from .registry import Registry
from .utils import UCFG

log = getLogger( __name__ )

@define( init=False )
class Application:

	_instance: ClassVar[Application] = None  # application singleton

	_ctx: ApplicationContext = field( default=None, alias='_ctx' )

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
		instance.__setup__( **kwargs )
		return instance

	# 'None' as default value means value has not been provided from the outside (via command line switch)
	def __setup__( self, *args, **kwargs ):
		# console logging setup --
		setup_console_logging( kwargs.get( 'verbose' ), kwargs.get( 'debug' ) )

		# create context, based on cfg_dir
		self._ctx = ApplicationContext( *args, **kwargs )

		# file logging setup after configuration has been loaded --
		setup_file_logging( self._ctx.verbose, self._ctx.debug, self._ctx.log_file_path )

		# print CLI configuration
		log.debug( f'triggered CLI with flags debug={kwargs}' )
		log.debug( f'using config dir: {self._ctx.config_dir} and library dir: {self._ctx.lib_dir}' )

		# open db from config_dir
		self._ctx.db = ActivityDb( path=self._ctx.db_dir_path, read_only=self._ctx.pretend, enable_index=self.ctx.config['db']['index'].get() )

		# ---- create service instances ----
		Registry.instantiate_services( ctx=self._ctx )

		# ---- announce context/configuration to utils module ----
		UCFG.reconfigure( self._ctx.config )

		# ---- register cleanup functions ----
		register_atexit( self._ctx.db.close )
		register_atexit( self._ctx.dump_state )

	# ---- context ---------------------------------------------------------------

	@property
	def ctx( self ) -> ApplicationContext:
		return self._ctx

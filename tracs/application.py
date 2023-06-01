
from __future__ import annotations

from atexit import register as register_atexit
from logging import DEBUG
from logging import INFO
from logging import FileHandler
from logging import Formatter
from logging import getLogger
from logging import StreamHandler
from sys import stderr

from tracs import activate_log_handler
from .config import ApplicationContext
from .config import APPNAME
from .db import ActivityDb
from .registry import Registry
from .utils import UCFG

log = getLogger( __name__ )

class Application( object ):

	_instance = None # application singleton

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
		# ---- create context, based on cfg_dir ----
		self._ctx = ApplicationContext( **kwargs )

		# ---- logging setup: only possible after configuration has been loaded --
		self._setup_logging( self._ctx )

		# print CLI configuration
		log.debug( f'triggered CLI with flags debug={ kwargs }' )
		log.debug( f'using config dir: {self._ctx.config_dir} and library dir: {self._ctx.lib_dir}' )

		# open db from config_dir
		self._ctx.db = ActivityDb( path=self._ctx.db_dir_path, read_only=self._ctx.pretend, enable_index=self.ctx.config['db']['index'].get() )

		# load plugins
		from tracs.registry import load as load_plugins
		load_plugins( ctx=self.ctx )

		# ---- create service instances ----
		Registry.instantiate_services( ctx=self._ctx )

		# ---- announce context/configuration to utils module ----
		UCFG.reconfigure( self._ctx.config )

		# ---- register cleanup functions ----
		register_atexit( self._ctx.db.close )
		register_atexit( self._ctx.dump_state )

	# noinspection PyMethodMayBeStatic
	def _setup_logging( self, ctx: ApplicationContext ):
		# not much to do here, just call activate log ...
		activate_log_handler( verbose=ctx.verbose, debug=ctx.debug, log_path=ctx.log_file_path )

	# ---- context ---------------------------------------------------------------

	@property
	def ctx( self ) -> ApplicationContext:
		return self._ctx

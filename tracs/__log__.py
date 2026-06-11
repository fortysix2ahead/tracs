from __future__ import annotations

from datetime import datetime
from logging import DEBUG, ERROR, FileHandler, Formatter, getLogger, INFO, Logger, WARNING
from pathlib import Path
from typing import ClassVar, Optional

from attrs import define, field
from dateutil.tz import UTC
from rich.logging import RichHandler
from rich.text import Text

from tracs.constants import APP_PKG_NAME

log = getLogger( __name__ )

DISABLE = 100

LOG_FILE_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
LOG_FILE_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

APP_TIME = datetime.now( tz=UTC )
LAST_LOG_TIME = datetime.now( tz=UTC )

def log_time_formatter( dt: str|datetime ) -> Text:
	global LAST_LOG_TIME

	dt_str = dt.strftime( "%H:%M:%S.%f" )
	delta = dt - LAST_LOG_TIME
	delta_str = f'{delta.seconds}.{str( delta.microseconds ).rjust( 6, "0" )}'
	LAST_LOG_TIME = dt

	return Text( f'{dt_str} +{delta_str}' )

DEFAULT_HANDLER: RichHandler = RichHandler( level=WARNING, show_time=False, show_level=False, markup=True )
VERBOSE_HANDLER: RichHandler = RichHandler( level=DISABLE, show_time=False, show_level=True, markup=True )
DEBUG_HANDLER: RichHandler = RichHandler( level=DISABLE, show_time=True, show_level=True, markup=True, log_time_format='%H:%M:%S' )
VERBOSE_DEBUG_HANDLER: RichHandler = RichHandler(
	level=DISABLE, show_time=True, show_level=True, markup=True, omit_repeated_times=False,
	log_time_format=log_time_formatter
)
FILE_HANDLER: Optional[FileHandler] = None

@define
class LogManager:

	_instance: ClassVar[LogManager|None] = None

	root: Logger = field( default=getLogger() )
	tracs_root: Logger = field( default=getLogger( APP_PKG_NAME ) ) # tracs root logger, not the system-wide root logger

	verbose: bool = field( default=False )
	debug: bool = field( default=False )
	json: bool = field( default=False )

	_active_handler: RichHandler = field( default=None, alias='_active_handler' )
	_active_file_handler: FileHandler = field( default=None, alias='_active_file_handler' )

	@classmethod
	def instance( cls, *args, **kwargs ) -> LogManager|None:
		if not LogManager._instance:
			LogManager._instance = LogManager( *args, **kwargs )
		return LogManager._instance

	def __attrs_post_init__( self ):
		self.tracs_root.setLevel( WARNING ) # initial level

		# add all handlers
		self.tracs_root.addHandler( DEFAULT_HANDLER )
		self.tracs_root.addHandler( VERBOSE_HANDLER )
		self.tracs_root.addHandler( DEBUG_HANDLER )
		self.tracs_root.addHandler( VERBOSE_DEBUG_HANDLER )

		# workaround to silence stravalib warnings
		from os import environ
		environ['SILENCE_TOKEN_WARNINGS'] = 'true'

		self.root.setLevel( ERROR )

	def _activate_handler( self, handler: RichHandler, level: int ) -> None:
		for h in self.tracs_root.handlers:
			if h == handler:
				h.setLevel( level )
			else:
				h.setLevel( DISABLE)
		self.tracs_root.setLevel( level )

	def set_console_log( self, verbose: bool = False, debug: bool = False, json: bool = False ):
		if debug and verbose:
			self._activate_handler( VERBOSE_DEBUG_HANDLER, DEBUG )
		elif debug:
			self._activate_handler( DEBUG_HANDLER, DEBUG )
		elif verbose:
			self._activate_handler( VERBOSE_HANDLER, INFO )
		else:
			self._activate_handler( DEFAULT_HANDLER, WARNING )

	def set_file_log( self, verbose: bool = False, debug: bool = False, log_path: Optional[Path] = None ):
		global FILE_HANDLER

		if log_path:
			file_handler = FileHandler( log_path, 'a' )
			file_handler.setFormatter( Formatter( LOG_FILE_FORMAT, LOG_FILE_DATE_FORMAT ) )
			file_handler.setLevel( DEBUG if debug else INFO )

			self.tracs_root.addHandler( file_handler )
			FILE_HANDLER = file_handler

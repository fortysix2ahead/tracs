from __future__ import annotations

from datetime import datetime
from logging import DEBUG, ERROR, FileHandler, Formatter, INFO, Logger, WARNING
from pathlib import Path
from typing import ClassVar

from attrs import define, field
from dateutil.tz import UTC
from rich.logging import RichHandler
from rich.text import Text

LOG_FILE_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
LOG_FILE_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

@define
class LogManager:

	_instance: ClassVar[LogManager] = None

	root: Logger = field( default=None ) # this is the tracs root logger, not the system-wide root logger
	apptime: datetime = field( default=datetime.now( UTC ) )
	last_log_time: datetime = field( default=datetime.now() )

	verbose: bool = field( default=False )
	debug: bool = field( default=False )
	json: bool = field( default=False )

	_active_handler: RichHandler = field( default=None, alias='_active_handler' )
	_active_file_handler: FileHandler = field( default=None, alias='_active_file_handler' )

	@classmethod
	def instance( cls, *args, **kwargs ) -> LogManager:
		if not LogManager._instance:
			LogManager._instance = LogManager( *args, **kwargs )
		return LogManager._instance

	@classmethod
	def log_time_formatter( cls, dt: str|datetime ) -> Text:
		dt_str = dt.strftime( "%H:%M:%S.%f" )
		delta = dt - cls.instance().last_log_time
		delta_str = f'{delta.seconds}.{str( delta.microseconds ).rjust( 6, "0" )}'
		cls.instance().last_log_time = dt
		return Text( f'{dt_str} +{delta_str}' )

	def __attrs_post_init__( self ):
		self.root.setLevel( DEBUG )
		self._active_handler = _default_handler
		self.root.addHandler( self._active_handler )

		# workaround to silence stravalib warnings
		from os import environ
		environ['SILENCE_TOKEN_WARNINGS'] = 'true'

		self.root.parent.setLevel( ERROR )

	def set_console_log( self, verbose: bool = False, debug: bool = False, json: bool = False ):
		self.root.removeHandler( self._active_handler )

		if debug and verbose:
			self._active_handler = _verbose_debug_handler
		elif debug:
			self._active_handler = _debug_handler
		elif verbose:
			self._active_handler = _verbose_handler
		else:
			self._active_handler = _default_handler

		self.root.addHandler( self._active_handler )

	def set_file_log( self, verbose: bool = False, debug: bool = False, log_path: Path = None ):
		if log_path:
			file_handler = FileHandler( log_path, 'a' )
			file_handler.setFormatter( Formatter( LOG_FILE_FORMAT, LOG_FILE_DATE_FORMAT ) )
			file_handler.setLevel( DEBUG if debug else INFO )

			if self._active_file_handler:
				self.root.removeHandler( self._active_file_handler )

			self._active_file_handler = file_handler
			self.root.addHandler( self._active_file_handler )

_default_handler: RichHandler = RichHandler( level=WARNING, show_time=False, show_level=False, markup=True )
_verbose_handler: RichHandler = RichHandler( level=INFO, show_time=False, show_level=True, markup=True )
_debug_handler: RichHandler = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, log_time_format='%H:%M:%S' )
_verbose_debug_handler: RichHandler = RichHandler(
	level=DEBUG, show_time=True, show_level=True, markup=True, omit_repeated_times=False,
	log_time_format=LogManager.log_time_formatter
)

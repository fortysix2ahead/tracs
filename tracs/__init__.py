from __future__ import annotations

from datetime import datetime, timedelta
from logging import DEBUG, FileHandler, Formatter, getLogger, INFO, WARNING
from pathlib import Path
from typing import Union

from dateutil.tz import tzlocal
from rich.logging import RichHandler
from rich.text import Text

APPLICATION_START_TIME = datetime.utcnow()
APPLICATION_START_TIME_LOCAL = APPLICATION_START_TIME.astimezone( tzlocal() )
LAST_LOG_TIME = datetime.now()

def log_time_formatter( dt: Union[str, datetime] ) -> Text:
	global LAST_LOG_TIME
	dt_str = dt.strftime( "%H:%M:%S.%f" )
	delta = dt - LAST_LOG_TIME
	delta_str = f'{delta.seconds}.{str( delta.microseconds ).rjust( 6, "0" )}'
	LAST_LOG_TIME = dt
	return Text( f'{dt_str} +{delta_str}' )

LOG_CONSOLE_DEFAULT_HANDLER = RichHandler( level=WARNING, show_time=False, show_level=False, markup=True )
LOG_CONSOLE_VERBOSE_HANDLER = RichHandler( level=INFO, show_time=False, show_level=True, markup=True )
LOG_CONSOLE_DEBUG_HANDLER = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, log_time_format='%H:%M:%S' )
LOG_CONSOLE_DEBUG_VERBOSE_HANDLER = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, omit_repeated_times=False, log_time_format=log_time_formatter )
# LOG_CONSOLE_DEBUG_HANDLER = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, log_time_format='%Y-%m-%d %H:%M:%S.%f' )

LOG_FILE_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
LOG_FILE_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# create root logger 'tracs'
log = getLogger( __name__ )

def activate_log_handler( verbose: bool = False, debug: bool = False, log_path: Path = None ):
	log.handlers.clear()
	if debug:
		log.setLevel( DEBUG )
		if verbose:
			log.addHandler( LOG_CONSOLE_DEBUG_VERBOSE_HANDLER )
		else:
			log.addHandler( LOG_CONSOLE_DEBUG_HANDLER )

	elif verbose:
		log.setLevel( INFO )
		log.addHandler( LOG_CONSOLE_VERBOSE_HANDLER )

	else:
		log.setLevel( WARNING )
		log.addHandler( LOG_CONSOLE_DEFAULT_HANDLER )

	if log_path:
		file_handler = FileHandler( log_path, 'a' )
		file_handler.setFormatter( Formatter( LOG_FILE_FORMAT, LOG_FILE_DATE_FORMAT ) )
		file_handler.setLevel( DEBUG if debug else INFO )
		log.addHandler( file_handler )

# activate default log handler
activate_log_handler()

def runtime() -> timedelta:
	return datetime.utcnow() - APPLICATION_START_TIME

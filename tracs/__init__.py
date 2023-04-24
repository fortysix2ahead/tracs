from logging import DEBUG, FileHandler, Formatter, getLogger, INFO, WARNING
from pathlib import Path

from rich.logging import RichHandler

LOG_CONSOLE_DEFAULT_HANDLER = RichHandler( level=WARNING, show_time=False, show_level=False, markup=True )
LOG_CONSOLE_VERBOSE_HANDLER = RichHandler( level=INFO, show_time=False, show_level=True, markup=True )
LOG_CONSOLE_DEBUG_HANDLER = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, log_time_format='%H:%M:%S' )
# LOG_CONSOLE_DEBUG_HANDLER = RichHandler( level=DEBUG, show_time=True, show_level=True, markup=True, log_time_format='%Y-%m-%d %H:%M:%S.%f' )

LOG_FILE_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
LOG_FILE_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# create root logger 'tracs'
log = getLogger( __name__ )

def activate_log_handler( verbose: bool = False, debug: bool = False, log_path: Path = None ):
	log.handlers.clear()
	if debug:
		log.setLevel( DEBUG )
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

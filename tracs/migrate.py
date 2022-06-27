
from pathlib import Path
from logging import getLogger
from shutil import copy
from sys import exit
from sys import modules

from rich.prompt import Confirm
from tinydb import TinyDB

from .config import ApplicationContext
from .db import document_cls
from .db_storage import DataClassStorage
from .utils import timestring

log = getLogger( __name__ )

def migrate_application( ctx: ApplicationContext, function_name: str = None, force: bool = False ):
	if not function_name:
		if ctx.db.schema != ctx.db.default_schema:
			function_name = f'_migrate_{ctx.db.schema}_{ctx.db.default_schema}'
		else:
			return

	current_db = ctx.db
	current_db_file = ctx.db_file

	next_db_file = Path( current_db_file.parent, current_db_file.name.replace( '.json', f'.migration_{timestring()}.json' ) )
	copy( current_db_file, next_db_file )
	next_db = TinyDB( storage=DataClassStorage, path=next_db_file, use_memory_storage=True, cache=True, document_factory=document_cls )

	if function_name and function_name in dir( modules[ __name__ ] ):
		if force or Confirm.ask( f'migration function {function_name} found, would you like to execute the migration?' ):
			getattr( modules[ __name__ ], function_name )( current_db, next_db )
	else:
		log.error( f'migration function "{function_name}" not found in module {__name__}' )

	exit( 0 )

def _migrate_11_12( current_db, next_db ):
	pass

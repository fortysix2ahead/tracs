from datetime import datetime
from logging import getLogger
from re import compile as rxcompile
from sys import maxsize, modules
from typing import List

from tracs.config import ApplicationContext

log = getLogger( __name__ )

FN_PREFIX = '_mdb_'
FN_REGEX = rxcompile( f'{FN_PREFIX}[a-z_]+' )

def migrate_db( ctx: ApplicationContext, function_name: str, **kwargs ):
	full_function_name = f'{FN_PREFIX}{function_name}'
	try:
		log.info( f'running db migration function {full_function_name}' )
		getattr( modules[__name__], full_function_name )( ctx, **kwargs )
	except RuntimeError as error:
		ctx.console.print( f'error executing db maintenance function {full_function_name}', error )

def migrate_db_functions( ctx: ApplicationContext ) -> List[str]:
	functions = [fn for fn in dir( modules[__name__] )]
	return sorted( [f.lstrip( FN_PREFIX ) for f in functions if FN_REGEX.fullmatch( f )] )

def _mdb_consolidate_activity_ids( ctx: ApplicationContext, **kwargs ) -> None:
	activities = sorted( ctx.db.activities, key=lambda activity: activity.starttime )
	ctx.db.activity_map.clear()
	for a, index in zip( activities, range( 1, maxsize ) ):
		ctx.db.activity_map[index] = a
	ctx.db.commit()

def _mdb_groups( ctx: ApplicationContext, **kwargs ) -> None:
	from orjson import loads, dumps
	from orjson import OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS
	ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	json = loads( ctx.db_fs.readbytes( 'activities.json' ) )
	activities = []
	for j in json:
		uids = j.get( 'uids' )
		if len( uids ) == 1:
			j['uid'] = j['uids'][0]
			del j['uids']
		elif len( uids ) > 1:
			dt = datetime.fromisoformat( j.get( 'starttime' ) )
			j['uid'] = f'group:{dt.strftime( "%y%m%d%H%M%S" )}'
		activities.append( j )

	ctx.db_fs.writebytes( 'activities2.json', dumps( activities, option=ORJSON_OPTIONS ) )

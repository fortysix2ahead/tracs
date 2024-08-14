from datetime import datetime
from logging import getLogger
from re import compile as rxcompile
from sys import maxsize, modules
from typing import List

from more_itertools import first_true
from orjson import loads, dumps
from orjson import OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS

from tracs.config import ApplicationContext
from tracs.uid import UID

log = getLogger( __name__ )

FN_PREFIX = '_mdb_'
FN_REGEX = rxcompile( f'{FN_PREFIX}[a-z_]+' )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

def migrate_db( ctx: ApplicationContext, function_name: str, **kwargs ):
	full_function_name = f'{FN_PREFIX}{function_name}'
	try:
		log.info( f'running db migration function {full_function_name}' )
		getattr( modules[__name__], full_function_name )( ctx, **kwargs )
	except AttributeError as error:
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
	json = loads( ctx.db_fs.readbytes( 'activities.json' ) )
	activities = []
	for j in json:
		uid, uids = j.get( 'uid' ), j.get( 'uids' )
		if not uid and uids:
			if len( uids ) == 1:
				j['uid'] = j['uids'][0]
				del j['uids']
			elif len( uids ) > 1:
				dt = datetime.fromisoformat( j.get( 'starttime' ) )
				j['uid'] = f'group:{dt.strftime( "%y%m%d%H%M%S" )}'
		activities.append( j )

	ctx.db_fs.writebytes( 'activities2.json', dumps( activities, option=ORJSON_OPTIONS ) )

def _mdb_schema( ctx: ApplicationContext, **kwargs ) -> None:
	activities = loads( ctx.db_fs.readbytes( 'activities.json' ) )
	resources = loads( ctx.db_fs.readbytes( 'resources.json' ) )

	for r in resources:
		p, t, uid = r['path'], r['type'], UID( uid=r['uid'] )
		li = str( uid.local_id )
		if uid.classifier in ['bikecitizens', 'polar', 'strava']:
			path = f'{uid.classifier}/{li[0]}/{li[1]}/{li[2]}/{li}/{p}'
		elif uid.classifier in [ 'waze', 'polarpersonaltrainer', 'local' ]:
			path = f'{uid.classifier}/{li[0:2]}/{li[2:4]}/{li[4:6]}/{li}/{p}'
		else:
			print( f'unhandled path {uid}' )

		if a := first_true( activities, pred=lambda a: a.get( 'uid' ) == str( uid ) ):
			a['resources'] = a.get( 'resources', [] )
			a['resources'].append( { 'path': path, 'type': t } )
		elif a := first_true( activities, pred=lambda a: str( uid ) in a.get( 'uids', [] ) ):
			a['metadata'] = { 'members': a.get( 'uids' ) }
			a['resources'] = a.get( 'resources', [] )
			a['resources'].append( { 'path': path, 'type': t } )
		else:
			print( f'unhandled resource: {r}' )

	for a in activities:
		a['resources'] = sorted( a.get( 'resources' ) or [], key=lambda r: r.get( 'path' ) )

	ctx.db_fs.writebytes( 'activities2.json', dumps( activities, option=ORJSON_OPTIONS ) )

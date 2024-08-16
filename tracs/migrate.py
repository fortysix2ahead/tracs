from datetime import datetime
from logging import getLogger
from re import compile as rxcompile
from sys import maxsize, modules
from typing import List

from orjson import dumps, loads, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS
from rich.pretty import pprint

from tracs.config import ApplicationContext

log = getLogger( __name__ )

FN_PREFIX = '_mdb_'
FN_REGEX = rxcompile( f'{FN_PREFIX}[a-z_]+' )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

def migrate_db( ctx: ApplicationContext, function_name: str, **kwargs ):
	full_function_name = f'{FN_PREFIX}{function_name}'
#	try:
	log.info( f'running db migration function {full_function_name}' )
	getattr( modules[__name__], full_function_name )( ctx, **kwargs )
#	except AttributeError as error:
#		ctx.console.print( f'error executing db maintenance function {full_function_name}', error )

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
	stages = [a for a in activities if a.get( 'resources' ) == []]
	multiparts = [a for a in activities if a.get( 'parts' )]

	for a in stages:
		if a.get( 'uid' ).endswith( '.gpx' ) or a.get( 'uid' ).endswith( '.tcx' ):
			a['uids'] = [ a['uid'] ]
		for uid in a.get( 'uids' ):
			uid, path = uid.split( '/' )
			a['resources'].append(
				{
					'path': f'{ctx.registry.services["polar"].path_for_uid( uid )}/{path}',
					'type': "application/gpx+xml" if path.endswith( '.gpx' ) else "application/tcx+xml"
				}
			)
		if a['uid'].startswith( 'group:' ):
			a['uid'] = f'polar:{datetime.fromisoformat( a["starttime"] ).strftime( "%y%m%d%H%M%S" )}'

		del a['uids']

	for a in multiparts:
		a['resources'] = [ r for r in a['resources'] if not ( r['path'].endswith( '.gpx' ) or r['path'].endswith( '.tcx' ) ) ]
		for p in a['parts']:
			uid, path = p['uids'][0].split( '/' )
			rid = f'{ctx.registry.services["polar"].path_for_uid( uid )}/{path}'
			stage = None
			for s in stages:
				stage_resources = [ u['path'] for u in s.get( 'resources', [] ) ]
				if rid in stage_resources:
					stage = s
					break

			if not stage:
				pprint( f'rid not found: {rid}' )
			else:
				p['uid'] = stage['uid']
				del p['uids']

	ctx.db_fs.writebytes( 'activities.json', dumps( activities, option=ORJSON_OPTIONS ) )

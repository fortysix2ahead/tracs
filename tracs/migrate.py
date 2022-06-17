
from pathlib import Path
from logging import getLogger
from shutil import copy
from sys import exit
from sys import modules

from rich.prompt import Confirm
from tinydb import TinyDB
from tinydb.operations import delete
from tinydb.operations import set
from tinydb.middlewares import CachingMiddleware
from tinydb import JSONStorage

from .config import GlobalConfig as gc
from .db import DB_VERSION
from .plugins.polar import _raw_id as polar_id

log = getLogger( __name__ )

def migrate_application( function_name: str = None ):
	if not function_name:
		db_schema = gc.db.default.all()[0].get( 'version' )
		current_schema = DB_VERSION
		if db_schema != current_schema:
			function_name = f'_migrate_{db_schema}_{current_schema}'
		else:
			return

	if function_name and function_name in dir( modules[ __name__ ] ):
		if Confirm.ask( f'migration function {function_name} found, would you like to execute the migration?' ):
			getattr( modules[ __name__ ], function_name )()
	else:
		log.error( f'migration function "{function_name}" not found in module {__name__}' )

	exit( 0 )

def _migrate_11_12():
	pass

# migrate db structure from 10 to 11
def _db_11() -> None:
	v11path = Path( gc.app.db_file.parent, 'db.v11.json' )
	copy( gc.app.db_file, v11path )
	v11db = TinyDB( v11path, indent=2, storage=CachingMiddleware( JSONStorage ) )
	v11db.table( '_default').update( { 'version': 11 }, doc_ids=[1] )
	activities = v11db.table( 'activities' )

	for doc in activities:
		if 'service' in doc:
			activities.update( set( '_classifier', doc['service'] ), doc_ids=[doc.doc_id] )
			activities.update( delete( 'service' ), doc_ids=[doc.doc_id] )
			if doc['service'] == 'polar':
				doc['_resources'] = []
				for field in ['gpx', 'csv', 'tcx', 'hrv']:
					if field in doc['_metadata']:
						status = doc['_metadata'][field]
						id = polar_id( doc['_raw'] )
						path = f'{id}.{field}' if not field == 'hrv' else f'{id}.{field}.csv'
						doc['_resources'].append(
							{
								'name': None,
								'type': field,
								'path': path,
								'status': status
							}
						)
						del doc['_metadata'][field]
				activities.update( set( '_resources', doc['_resources'] ), doc_ids=[doc.doc_id] )
			elif doc['service'] == 'strava':
				doc['_resources'] = []
				for field in ['gpx', 'tcx']:
					if field in doc['_metadata']:
						status = doc['_metadata'][field]
						path = f"{doc['_raw']['id']}.{field}"
						doc['_resources'].append(
							{
								'name': None,
								'type': field,
								'path': path,
								'status': status
							}
						)
						del doc['_metadata'][field]
				activities.update( set( '_resources', doc['_resources'] ), doc_ids=[doc.doc_id] )
			elif doc['service'] == 'waze':
				doc['_resources'] = [{
					'name': None,
					'type': 'gpx',
					'path': f"{doc['_raw']['id']}.gpx",
					'status': 100
				}]
				activities.update( set( '_resources', doc['_resources'] ), doc_ids=[doc.doc_id] )
				if 'gpx' in doc['_metadata']:
					del doc['_metadata']['gpx']
				doc['_metadata']['source_path'] = doc['_raw']['path']
				del( doc['_raw']['path'] )

		if '_metadata' in doc and 'groups' in doc['_metadata']:
			if 'parent' in doc['_metadata']['groups']:
				d = {'parent': doc['_metadata']['groups']['parent']}
				activities.update( set( '_groups', d ), doc_ids=[doc.doc_id] )
				del ( doc['_metadata']['groups'] )
			elif 'ids' in doc['_metadata']['groups']:
				d = {
					'ids': doc['_metadata']['groups']['ids'],
					'uids': doc['_metadata']['groups']['eids'],
				}
				activities.update( set( '_groups', d ), doc_ids=[doc.doc_id] )
				del( doc['_metadata']['groups'] )

		if '_metadata' in doc:
			activities.update( set( '_metadata', doc['_metadata'] ), doc_ids=[doc.doc_id] )

	v11db.storage.flush()

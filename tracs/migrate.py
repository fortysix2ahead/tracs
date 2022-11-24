
from pathlib import Path
from logging import getLogger
from shutil import copy
from sys import exit
from sys import modules

from rich.prompt import Confirm
from tinydb import TinyDB

from .config import ApplicationContext
from .db_storage import DataClassStorage
from .plugins.handlers import JSONHandler
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
	next_db = TinyDB( storage=DataClassStorage, path=next_db_file, read_only=True )

	if function_name and function_name in dir( modules[ __name__ ] ):
		if force or Confirm.ask( f'migration function {function_name} found, would you like to execute the migration?' ):
			getattr( modules[ __name__ ], function_name )( current_db, next_db )
	else:
		log.error( f'migration function "{function_name}" not found in module {__name__}' )

	exit( 0 )

def _migrate_11_12( current_db, next_db ):
	pass

def consolidate_ids( current_db, next_db ):
	json = JSONHandler().load( path=current_db.activities_path ).raw

	activity_list = []
	for doc_id, a in json.raw['_default'].items():
		activity_list.append( ( doc_id, None, a ) )

	activity_list = sorted( activity_list, key = lambda t: t[2]['time'] )

	new_dict = {}
	for index in range( len( activity_list ) ):
		new_index = str( index + 1 )
		new_dict[new_index] = activity_list[index][2]
	new_dict = { '_default': new_dict }

	JSONHandler().save( data = new_dict, path=Path( current_db.activities_path.parent, 'activities_consolidated.json' ) )

def migrate_resources( current_db, next_db ):
	json = JSONHandler().load( path=current_db.activities_path ).raw
	resource_json = JSONHandler().load( path=current_db.resources_path ).raw

	table = json['_default']
	resource_table = resource_json['_default']
	resource_counter = 1

	for doc_id, doc in table.items():
		classifier = doc.get( 'classifier' )
		raw_id = doc.get( 'raw_id' )
		resources = doc.get( 'resources' )
		resource_ids = []

		if classifier != 'group':
			for r in resources:
				r['uid'] = f'{classifier}:{raw_id}'
				resource_table[str( resource_counter )] = r
				resource_ids.append( resource_counter )
				resource_counter += 1
			if len( resource_ids ) > 0:
				doc['resources'] = resource_ids

	items = list( table.items() )
	for doc_id, doc in items:
		classifier = doc.get( 'classifier' )
		if classifier == 'group':
			doc['uids'] = doc['group_uids']

			del (doc['classifier'])
			del( doc['raw_id'] )
			del( doc['resources'] )
			del( doc['metadata'] )
			del( doc['group_ids'] )
			del( doc['group_uids'] )
		else:
			if doc.get( 'parent_id', 0 ) > 0:
				del( table[doc_id] )
			else:
				doc['uids'] = [f'{doc.get( "classifier" )}:{doc.get( "raw_id" )}']
				del (doc['classifier'])
				del (doc['raw_id'])
				del (doc['resources'])
				del (doc['metadata'])

	#JSONHandler().save( Path( current_db.activities_path.parent, 'test.json' ), json )
	JSONHandler().save( Path( current_db.activities_path ), json )
	JSONHandler().save( current_db.resources_path, resource_json )

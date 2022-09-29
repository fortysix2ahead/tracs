from dataclasses import fields
from pathlib import Path
from re import match
from re import split

from confuse.exceptions import NotFoundError
from logging import getLogger
from rich import box
from rich.pretty import Pretty as pp
from rich.table import Table

from .activity import Activity
from .config import ApplicationConfig as cfg
from .config import GlobalConfig as gc
from .config import console
from .dataclasses import PERSIST
from .dataclasses import PROTECTED
from .plugins import Registry
from .utils import fmt
from .utils import red

log = getLogger( __name__ )

FILE_EXISTS = '\u2705' # file has been downloaded
FILE_MISSING = '\u2716' # file is missing (does not exist on server)
FILE_NEEDS_DOWNLOAD = '\u25EF' # file is missing, but might exist on the server
FILE_NEEDS_DOWNLOAD = '\u21A9' # file is missing, but might exist on the server

def list_activities( activities: [Activity], sort: str, format_name: str ) -> None:
	# sort list before printing
	if sort == 'id':
		activities.sort( key=lambda x: x.doc_id )
	elif sort == 'name':
		activities.sort( key=lambda x: x.name )
	elif sort == 'date':
		activities.sort( key=lambda x: x.time )
	elif sort == 'type':
		activities.sort( key=lambda x: x.type )

	try:
		list_format = cfg['formats']['list'][format_name].get()
	except NotFoundError:
		list_format = cfg['formats']['list']['default'].get()
	list_fields = list_format.split()

	headers = []

	for f in list_fields:
		if m := match( '^(\w+)\.(\w+)$', f ):
			headers.append( f'{m.groups()[1].capitalize()} [{m.groups()[0].capitalize()}]' )
		else:
			headers.append( f.capitalize() )

	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )

	table.add_column( '[blue]id' )
	table.add_column( '[blue]name' )
	table.add_column( '[blue]type' )
	table.add_column( '[blue]local time' )
	table.add_column( '[blue]uid' )

	for a in activities:
		table.add_row( pp( a.doc_id ), a.name, fmt( a.type ), fmt( a.localtime ), pp( a.uids ) )

	if len( table.rows ) > 0:
		console.print( table )

def inspect_activities( activities: [Activity] ) -> None:
	for a in activities:
		table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

		table.add_row( '[blue]field[/blue]', '[blue]type[/blue]', '[blue]value[/blue]', '[blue]protected[/blue]', '[blue]persist[/blue]' )

		for f in sorted( Activity.fields(), key=lambda field: field.name ):
			table.add_row( f.name, f.type, pp( getattr( a, f.name ) ), pp( f.metadata.get( PROTECTED, False ) ), pp( f.metadata.get( PERSIST, True ) ) )

		console.print( table )

def inspect_resources() -> None:
	raise NotImplementedError

def inspect_registry() -> None:
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

	table.add_row( '[bold bright_blue]Services[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]display name[/blue]', '[blue]class[/blue]', '[blue]enabled[/blue]' )
	for key, value in Registry.services.items():
		table.add_row( value.name, value.display_name, pp( value.__class__ ), pp( value.enabled ) )

	table.add_row( '[bold bright_blue]Document Classes[/bold bright_blue]' )
	table.add_row( '[blue]type[/blue]', '[blue][/blue]', '[blue]class[/blue]' )

	for key, value in Registry.document_classes.items():
		table.add_row( key, '', pp( f'{value.__module__}.{value.__name__}' ) )

	table.add_row( '[bold bright_blue]Importers[/bold bright_blue]' )
	table.add_row( '[blue]type[/blue]', '[blue][/blue]', '[blue]class[/blue]' )

	for key, value in Registry.importers.items():
		for v in value:
			table.add_row( key, '', pp( v.__class__ ) )

	console.print( table )

def show_fields():
	for f in fields( Activity ):
		console.print( f'{f.name} <{f.type}>' )

def show_config():
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_column( justify='left', no_wrap=True )
	table.add_column( justify='left', no_wrap=True )

	table.add_row( 'configuration file', pp( gc.app.cfg_file ) )
	table.add_row( 'state file', pp( gc.app.state_file ) )
	table.add_row( 'library', pp( gc.app.lib_dir ) )
	table.add_row( 'database file', pp( gc.app.db_file ) )
	table.add_row( 'database backup', pp( gc.app.backup_dir ) )

	for s in gc.app.services.values():
		table.add_row( f'{s.display_name} activities:', pp( Path( gc.app.db_dir, s.name ) ) )

	console.print( 'Locations', style='bold' )
	console.print( table )

	console.print( 'Configuration', style='bold' )
	console.print( gc.app.cfg.dump() )

def shorten( s: str ) -> str:
	max_length = 120
	if len( str( s ) ) > max_length:
		start = int( max_length / 2 )
		end = int( len( str( s ) ) - (max_length / 2) )
		return f"{str( s )[:start]}{red('... ...')}{str( s )[end:]}"
	else:
		return s

def _type( o ) -> str:
	s = split( '^<.+\'(.+)\'>$', str( type( o ) ) )
	return s[1] if len( s ) > 2 else str( type( o ) )

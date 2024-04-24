
from logging import getLogger
from pathlib import Path
from re import split
from typing import List

from dynaconf.vendor.box.exceptions import BoxKeyError
from rich import box
from rich.pretty import Pretty as pp
from rich.table import Table

from .activity import Activity
from .config import ApplicationContext
from .config import console
from .core import VirtualField
from .registry import Registry
from .ui.utils import style
from .utils import fmt
from .utils import red

log = getLogger( __name__ )

def list_activities( activities: List[Activity], sort: str = False, reverse: bool = False, format_name: str = False, ctx: ApplicationContext = None ) -> None:
	sort = sort or 'starttime'

	if sort in Activity.field_names():
		activities.sort( key=lambda act: getattr( act, sort, None ) )
	else:
		log.warning( f'ignoring unknown sort field "{sort}", falling back to "time"' )

	if reverse:
		activities.reverse()

	try:
		list_format = ctx.config['formats']['list'][format_name]
	except BoxKeyError:
		list_format = ctx.config['formats']['list']['default']
	list_fields = list_format.split()

	headers = [ f for f in list_fields ]
	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )

	for h in headers:
		table.add_column( f'[blue]{h}' )

	for a in activities:
		table.add_row( *[ fmt( a.getattr( f ) ) for f in list_fields ] )

	if len( table.rows ) > 0:
		console.print( table )

def inspect_activities( activities: [Activity] ) -> None:
	for a in activities:
		table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

		table.add_row( '[blue]field[/blue]', '[blue]type[/blue]', '[blue]value[/blue]' )

		for f in sorted( Activity.fields(), key=lambda field: field.name ):
			table.add_row( f.name, pp( f.type ), pp( getattr( a, f.name ) ) )

		console.print( table )

def inspect_resources() -> None:
	raise NotImplementedError

def inspect_plugins( ctx: ApplicationContext ) -> None:
	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
	table.add_column( '[bold bright_blue]name[/bold bright_blue]' )
	table.add_column( '[bold bright_blue]plugin[/bold bright_blue]' )

	[ table.add_row( n, str( p ) ) for n, p in ctx.plugins.items() ]

	ctx.console.print( table )

def inspect_registry( registry: Registry ) -> None:
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

	table.add_row( '[bold bright_blue]Services[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]class[/blue]', '[blue]display name[/blue]', '[blue]enabled[/blue]' )
	for k, v in sorted( registry.services.items(), key=lambda i: i[1].name ):
		table.add_row( v.name, pp( v.__class__ ), v.display_name, pp( v.enabled ) )

	table.add_row( '[bold bright_blue]Virtual Fields[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]type[/blue]', '[blue]display name[/blue]' )
	for k, v in sorted( registry.virtual_fields.items(), key=lambda i: i[1].name ):
		table.add_row( v.name, pp( v.type ), v.display_name )

	table.add_row( '[bold bright_blue]Keywords[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]expression[/blue]', '[blue]description[/blue]' )
	for k, v in sorted( registry.keywords.items(), key=lambda i: i[0] ):
		table.add_row( v.name, pp( v.expr or v.fn ), v.description )

	table.add_row( '[bold bright_blue]Normalizers[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]type[/blue]', '[blue]description[/blue]' )
	for k, v in sorted( registry.normalizers.items(), key=lambda i: i[0] ):
		table.add_row( v.name, pp( v.type ), v.description )

	table.add_row( '[bold bright_blue]Importers[/bold bright_blue]' )
	table.add_row( '[blue]type[/blue]', '[blue]class[/blue]', '[blue][/blue]' )
	for k, v in sorted( registry.importers.items(), key=lambda i: i[0] ):
		table.add_row( k, pp( v.__class__ ), '' )

	table.add_row( *style( 'Resource Types', style='bold bright_blue' ) )
	table.add_row( *style( 'type', 'class', 'summary, recording, image', style='blue' ) )
	for k, v in sorted( registry.resource_types.items(), key=lambda i: i[0] ):
		flags = [ v.summary, v.recording, v.image ]
		table.add_row( k, pp( v.activity_cls ), pp( flags ) )

	table.add_row( '[bold bright_blue]Setup Functions[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]function[/blue]' )
	[ table.add_row( k, pp( f ) ) for k, f in sorted( registry.setups.items(), key=lambda i: i[0] ) ]

	console.print( table )

def show_fields():
	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
	table.caption, table.caption_justify = 'Virtual fields are marked with \u24e5  and shown in yellow.', 'left'
	table.add_column( '', justify='center' )
	table.add_column( 'field' )
	table.add_column( 'type' )

	for f in sorted( Activity.fields( include_internal=False, include_virtual=True ), key=lambda fld: fld.name ):
		# name = f'{f.name} \u24e5' if isinstance( f, VirtualField ) else f.name
		virtual = '[yellow]\u24e5[/yellow]' if isinstance( f, VirtualField ) else ''
		name = f'[yellow]{f.name}[/yellow]' if isinstance( f, VirtualField ) else f.name
		table.add_row( virtual, name, pp( f.type ) )

	console.print( table )

def show_config( ctx: ApplicationContext ):
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_column( justify='left', no_wrap=True )
	table.add_column( justify='left', no_wrap=True )

	table.add_row( 'configuration dir', ctx.config_dir )
	table.add_row( 'configuration file', pp( ctx.config_file ) )
	table.add_row( 'state file', pp( ctx.state_file ) )

	table.add_section()

	table.add_row( 'library', pp( ctx.lib_dir ) )
	table.add_row( 'database dir', pp( ctx.db_dir ) )

	table.add_section()

	for s in ctx.registry.services.values():
		table.add_row( f'{s.name} activities:', pp( Path( ctx.db_dir, s.name ) ) )

	table.add_section()

	#table.add_row( 'plugins dir', pp( ctx.plugins_dir ) )
	#table.add_row( 'overlay dir', pp( ctx.overlay_dir ) )

	console.print( 'Locations', style='bold' )
	console.print( table )

	console.print( 'Configuration', style='bold' )
	console.print( ctx.config.dump() )

	console.print( 'State', style='bold' )
	console.print( ctx.state.dump() )

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

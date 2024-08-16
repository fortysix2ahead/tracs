from orjson import dumps
from rich import box
from rich.pretty import Pretty as pp
from rich.table import Table

from tracs.activity import Activity
from tracs.config import ApplicationContext, console
from tracs.pluginmgr import PluginManager
from tracs.registry import Registry
from tracs.ui.utils import style

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

	[ table.add_row( n, str( p ) ) for n, p in PluginManager.plugins.items() ]

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
		table.add_row( k, pp( v.type ), pp( flags ) )

	table.add_row( '[bold bright_blue]Setup Functions[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]function[/blue]' )
	[ table.add_row( k, pp( f ) ) for k, f in sorted( registry.setups.items(), key=lambda i: i[0] ) ]

	console.print( table )

def inspect_keywords( ctx: ApplicationContext, as_json: bool ) -> None:
	keywords = sorted( ctx.registry.keywords.items() )
	if as_json:
		json = [ { 'name': k } for k, v in keywords ]
		console.print_json( dumps( json ).decode(), sort_keys=True )
	else:
		table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
		table.add_column( '[bold bright_blue]name[/bold bright_blue]' )
		for k, v in keywords:
			table.add_row( k )
		ctx.console.print( table )

from attrs import asdict
from orjson import dumps
from rich import box
from rich.pretty import Pretty as pp
from rich.table import Table

from tracs.activity import Activity
from tracs.protocols import ApplicationContext
from tracs.pluginmgr import PluginManager, Registry
from tracs.ui import CONSOLE as cs
from tracs.ui.utils import style

def inspect_activities( activities: [Activity] ) -> None:
	for a in activities:
		table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

		table.add_row( '[blue]field[/blue]', '[blue]type[/blue]', '[blue]value[/blue]' )

		for f in sorted( Activity.fields(), key=lambda field: field.name ):
			table.add_row( f.name, pp( f.type ), pp( getattr( a, f.name ) ) )

		cs.print( table )

def inspect_resources() -> None:
	raise NotImplementedError

def inspect_plugins( ctx: ApplicationContext ) -> None:
	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
	table.add_column( '[bold bright_blue]name[/bold bright_blue]' )
	table.add_column( '[bold bright_blue]module[/bold bright_blue]' )

	[ table.add_row( p.__name__, str( p ) ) for p in PluginManager.inst().plugins ]

	cs.print( table )

def inspect_registry( registry: Registry ) -> None:
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

	table.add_row( '[bold bright_blue]Service Classes[/bold bright_blue]' )
	table.add_row( '[blue]class[/blue]' )
	for k in sorted( registry.services, key=lambda i: i.__name__ ):
		table.add_row( pp( k ) )

	table.add_row( '[bold bright_blue]Virtual Fields[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]type[/blue]', '[blue]display name[/blue]' )
	for k in sorted( registry.virtual_fields, key=lambda i: i.name ):
		table.add_row( k.name, pp( k.type ), k.display_name )

	table.add_row( '[bold bright_blue]Keywords[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]expression[/blue]', '[blue]description[/blue]' )
	for k in sorted( registry.keywords, key=lambda i: i.name ):
		table.add_row( k.name, pp( k.expr or k.fn ), k.description )

	table.add_row( '[bold bright_blue]Normalizers[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]type[/blue]', '[blue]description[/blue]' )
	for k in sorted( registry.normalizers, key=lambda i: i.name ):
		table.add_row( k.name, pp( k.type ), k.description )

	table.add_row( '[bold bright_blue]Importers[/bold bright_blue]' )
	table.add_row( '[blue][/blue]', '[blue]class[/blue]', '[blue][/blue]' )
	for k in sorted( registry.importers, key=lambda i: i.__name__ ):
		table.add_row( '', pp( k ), '' )

	table.add_row( *style( 'Resource Types', style='bold bright_blue' ) )
	table.add_row( *style( 'type', 'class', 'summary, recording, image', style='blue' ) )
	for k in sorted( registry.resource_types(), key=lambda i: i.name ):
		flags = [ k.summary, k.recording, k.image ]
		table.add_row( pp( k.name ), pp( k.__class__ ), pp( flags ) )

	table.add_row( '[bold bright_blue]Setup Functions[/bold bright_blue]' )
	table.add_row( '[blue]name[/blue]', '[blue]function[/blue]' )
	for k in registry.setups:
		table.add_row( '', pp( k ) )

	cs.print( table )

def inspect_keywords( ctx: ApplicationContext, as_json: bool ) -> None:
	keywords = sorted( ctx.registry.keywords, key=lambda k: k.name )
	if as_json:
		cs.print_json( dumps( [ asdict( k ) for k in keywords ] ).decode(), sort_keys=True )
	else:
		table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
		table.add_column( '[bold bright_blue]name[/bold bright_blue]' )
		table.add_column( '[bold bright_blue]description[/bold bright_blue]' )
		table.add_column( '[bold bright_blue]expression[/bold bright_blue]' )
		for k in keywords:
			table.add_row( k.name, k.description, k.expr )
		cs.print( table )

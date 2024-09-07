
from logging import getLogger
from typing import List

from rich import box
from rich.pretty import Pretty as pp
from rich.prompt import Confirm
from rich.table import Table

from tracs.config import ApplicationContext, console
from tracs.registry import Registry

log = getLogger( __name__ )

app_setup_text = 'This creates a valid application setup by asking a few questions (mainly credentials). Credentials and ' \
                 'options will be saved in the configuration file, while variable data will go into an application ' \
                 'state file.'

def setup_old( ctx: ApplicationContext, services: List[str] ):
	console.clear()

	console.rule( "[bold]Application Setup[/bold]" )
	console.print( app_setup_text, soft_wrap=True )

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'Configuration file:', pp( ctx.cfg_file ) )
	table.add_row( 'State file:', pp( ctx.state_file) )

	console.print( table )

	if services:
		service_names = [ *services ]
	else:
		service_names = [*Registry.services.keys()]

	for name in service_names:
		answer = Confirm.ask( f'Would you like to setup {name}?', default=False )
		if answer:
			console.print()
			console.rule( f'[bold]Setup {name}[/bold]' )
			Registry.services.get( name ).setup( ctx )
			console.print()

	ctx.dump_config_state()

def setup( ctx: ApplicationContext, services: List[str] ):
	ctx.console.clear()

	ctx.console.rule( "[bold]Application Setup[/bold]" )
	ctx.console.print( app_setup_text, width=120 )

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( 'Configuration file:', pp( ctx.config_file_path ) )
	table.add_row( 'State file:', pp( ctx.state_file_path ) )
	ctx.console.print( table )

	service_names = services if services else ctx.registry.setups.keys()

	for name in service_names:
		answer = ctx.force or Confirm.ask( f'Would you like to run setup function for plugin {name}?', default=False )
		if answer:
			console.print()
			console.rule( f'[bold]Setup {name}[/bold]' )
			setup_function = ctx.registry.setups.get( name )
			config_key = name.split( '.' )[-1]
			if setup_function:
				existing_config = ctx.config.plugins[config_key]
				existing_state = ctx.state.plugins[config_key]
				config, state = setup_function( ctx, existing_config, existing_state )
				ctx.config['plugins'][config_key] = { **existing_config, **config }
				ctx.state['plugins'][config_key] = { **existing_state, **state }
				console.print()

	ctx.dump_config_state()


from logging import getLogger

from rich import box
from rich.pretty import Pretty as pp
from rich.prompt import Confirm
from rich.table import Table

from .config import ApplicationContext
from .config import console
from .plugins import Registry

log = getLogger( __name__ )

app_setup_text = 'This creates a valid application setup by asking a few questions (mainly credentials). Credentials and ' \
                 'options will be saved in the configuration file, while variable data will go into an application ' \
                 'state file.'

def setup( ctx: ApplicationContext, services ):
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

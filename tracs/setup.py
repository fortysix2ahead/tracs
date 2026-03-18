
from logging import getLogger
from typing import List

from rich import box
from rich.pretty import Pretty as pp
from rich.prompt import Confirm, Prompt
from rich.table import Table

from tracs.protocols import ApplicationContext
from tracs.ui import CONSOLE as c

log = getLogger( __name__ )

app_setup_text = \
'''This creates a valid application setup by asking a few questions (mainly
credentials). Credentials and options will be saved in the configuration file,
while variable data like access tokens will go into an application state file.

The application is configured to use the following files:
Config: \"{config_file}\"
State: \"{state_file}\"

'''

def setup( ctx: ApplicationContext, services: List[str] ):
	c.clear()

	c.rule( "[bold]Setup[/bold]" )
	text = app_setup_text.format( config_file=ctx.config_file_path, state_file=ctx.state_file_path )
	c.print( text, width=120 )

	for s in services:
		if current_config := ctx.config.services.get( s ):
			c.print( f'A configuration for service [blue]{s}[/blue] already exists.' )

			answer = Prompt.ask(
				f'Would you like to run the setup again or \[s]how the current configuration/state?',
				choices=['y', 'n', 's'], show_default=True, show_choices=True )

			match answer:
				case 'y':
					run_setup, ask_again = True, False
				case 's':
					for k, v in current_config.items():
						c.print( f'  {k}: {v}' )
					c.print()
					run_setup, ask_again = False, True
				case _:
					return

			if ask_again:
				run_setup = Confirm.ask( f'Would you like to run the setup now?', default=False )

		else:
			c.print( f'No configuration for service [blue]{s}[/blue] exists, running setup ...' )
			run_setup = True

		if run_setup:
			# todo: this will fail for fresh services as they won't be instantiated -> bootstrapping necessary
			ctx.service_mgr.get( s ).setup()
			ctx.dump_config_state()

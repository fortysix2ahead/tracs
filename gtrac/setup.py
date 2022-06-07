
from logging import getLogger

from .config import GlobalConfig as gc
from .config import console
from .ui import InstantConfirm as Confirm

log = getLogger( __name__ )

app_setup_text = 'This creates a valid application setup by asking a few questions (mainly credentials). Credentials and ' \
                 'options will be saved in the configuration file, while variable data will go into an application ' \
                 'state file.'

def setup():
	app = gc.app

	console.clear()

	console.rule( "[bold]Application Setup" )
	console.print( app_setup_text, soft_wrap=True )
	console.print( f'Configuration file: {app.cfg_file}' )
	console.print( f'State file: {app.state_file}' )
	console.print()

	for name, s in app.services.items():
		answer = Confirm.ask( f'Would you like to setup {s.display_name}?', default=False )
		if answer:
			console.print()
			console.rule( f'[bold]Setup {s.display_name}' )
			s.setup()
			console.print()

	app.dump_cfg()
	app.dump_state()

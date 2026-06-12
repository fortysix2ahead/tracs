
from logging import getLogger

log = getLogger( __name__ )

if __name__ == '__main__':
	from tracs.application import Application
	app = Application.instance()

	from tracs.cli import cli
	cli()

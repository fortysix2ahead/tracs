
from logging import getLogger

log = getLogger( __name__ )

def main():
	from tracs.application import Application
	app = Application.instance()

	from tracs.cli import cli
	cli()

if __name__ == '__main__':
	main()


from sys import stderr
from logging import DEBUG
from logging import INFO
from logging import Formatter
from logging import StreamHandler
from logging import getLogger
from pathlib import Path
from datetime import datetime

from click import argument
from click import echo
from click import option
from click import prompt
from click import Choice
from click import Path as ClickPath
from click_shell import shell

from .activity import Activity
from .application import Application
from .config import ApplicationConfig as cfg
from .config import GlobalConfig as gc
from .config import APPNAME
from .db import backup_db
from .db import restore_db
from .db import status_db
from .edit import edit_activities
from .group import group_activities
from .group import ungroup_activities
from .group import part_activities
from .group import unpart_activities
from .io import export_csv
from .io import export_geojson
from .io import export_gpx
from .io import export_kml
from .io import export_shp
from .io import reimport_activities
from .list import inspect_activities
from .list import list_activities
from .list import show_fields
from .list import show_activity
from .list import show_config
from .edit import rename_activities
from .migrate import migrate_application
from .plugins import Registry
from .validate import validate_activities
from .setup import setup as setup_application
from .service import download_activities
from .service import link_activities

log = getLogger( __name__ )

#@group()
#@pass_context
@shell( prompt=f'{APPNAME} > ', intro=f'Starting interactive shell mode, enter <exit> to leave this mode again, use <{APPNAME} --help> for help ...' )
@option( '-c', '--configuration', is_flag=False, required=False, help='configuration area location', metavar='PATH' )
@option( '-l', '--library', is_flag=False, required=False, help='library location', metavar='PATH' )
@option( '-v', '--verbose', is_flag=True, default=None, required=False, help='be more verbose when logging' )
@option( '-d', '--debug', is_flag=True, default=None, required=False, help='enable output of debug messages' )
@option( '-f', '--force', is_flag=True, default=None, required=False, help='forces operations to be carried out' )
@option( '-p', '--pretend', is_flag=True, default=None, required=False, help='pretends to work, only simulates everything and does not persist any changes' )
def cli( configuration, debug, force, library, verbose, pretend ):
	_init_logging( debug )

	if debug:
		getLogger( __package__ ).setLevel( DEBUG )
		getLogger( __package__ ).handlers[0].setLevel( DEBUG ) # this should not fail as the handler is defined in __main__

	log.debug( f'triggered CLI with flags debug={debug}, verbose={verbose}, force={force}, pretend={pretend}' )

	gc.app = Application.instance(
		config_dir=Path( configuration ) if configuration else None,
		lib_dir=Path( library ) if library else None,
		verbose=verbose,
		debug=debug,
		force=force,
		pretend=pretend
	)

@cli.command( hidden=True )
@option( '-b', '--backup', is_flag=True, required=False, help='creates a backup of the internal database' )
@option( '-f', '--fields', is_flag=True, required=False, hidden=True, help='shows available fields, which can be used for queries (EXPERIMENTAL!)' )
@option( '-m', '--migrate', is_flag=False, required=False, type=str, help='performs a database migration', metavar='FUNCTION' )
@option( '-r', '--restore', is_flag=True, required=False, help='restores the last version of the database from the backup' )
@option( '-s', '--status', is_flag=True, required=False, help='prints some db status information' )
def db( backup: bool, fields: bool, migrate: str, restore: bool, status: bool ):
	app = Application.instance()
	if backup:
		backup_db( app.db_file, app.backup_dir )
	elif fields:
		show_fields()
	elif migrate:
		migrate_application( function_name=migrate )
	elif restore:
		restore_db( app.db.db, app.db_file, app.backup_dir, app.cfg['force'].get() )
	elif status:
		status_db( app.db, app.services )

@cli.command( help='prints the current configuration' )
def config():
	show_config()

@cli.command( help='synchronizes fitness data' )
@option( '-a', '--all', 'all_', is_flag=True, required=False, help='synchonizes all activities (instead of recent ones)' )
@option( '-r', '--restrict', is_flag=False, required=False, help='restricts sync to only one source', metavar='SERVICE' )
def sync( all_: bool = False, restrict: str = None ):
	for s in Application.instance().services.values():
		if restrict is None or restrict.lower() == s.name:
			activities = s.fetch( fetch_all=all_ )
			s.download( activities )
			s.link( activities )

@cli.command( help='fetches activity ids' )
@option( '-a', '--all', 'all_', is_flag=True, required=False, help='fetches all activities (instead of activities from last known onwards)' )
@option( '-r', '--restrict', is_flag=False, required=False, help='restricts fetching to only one source', metavar='SERVICE' )
def fetch( all_: bool = False, restrict: str = None ):
	for name, service in Registry.services.items():
		if restrict is None or restrict == name:
			service.fetch( all_ )

@cli.command( help='downloads activities' )
@option( '-a', '--all', 'all_', is_flag=True, required=False, help='downloads all activities (instead of recent ones only), overriding provided filters' )
@argument( 'filters', nargs=-1 )
def download( filters, all_ ):
	if all_:
		download_activities( gc.db.find( [], False, True, True ) )
	else:
		download_activities( gc.db.find( filters, False, True, True ) )

@cli.command( help='creates links for downloaded resources of activities' )
@option( '-a', '--all', 'all_', is_flag=True, required=False, help='creates links for all activities (instead of recent ones only), overriding provided filters' )
@argument( 'filters', nargs=-1 )
def link( all_, filters ):
	if all_:
		link_activities( gc.db.find( [], False, True, True ) )
	else:
		link_activities( gc.db.find( filters, False, True, True ) )

def _filter_activities( all_, filters ) -> [Activity]:
	app = Application.instance()
	if all_:
		activities = app.db.all()
	else:
		if filters:
			activities = app.db.find( filters )
		else:
			activities = app.db.find( [ f"time:{datetime.utcnow().year}" ] )

	return activities

@cli.command( 'list', help='lists activities' )
@option( '-s', '--sort', is_flag=False, required=False, type=Choice(['id', 'name', 'date', 'type'], case_sensitive=False), help='sorts the output according to an attribute' )
@option( '-f', '--format', 'format_name', is_flag=False, required=False, type=str, hidden=True, help='uses the format with the provided name when printing', metavar='FORMAT' )
@option( '-g', '--include-grouped', is_flag=True, required=False, help='include grouped activities' )
@argument('filters', nargs=-1)
def ls( sort, format_name, filters, include_grouped ):
	list_activities( gc.db.find( filters, True, include_grouped, True ), sort, format_name )

@cli.command( help='shows details about activities' )
@option( '-f', '--format', 'frmt', is_flag=False, required=False, type=str, hidden=True, help='uses the provided format string when printing', metavar='FORMAT' )
@option( '-r', '--raw', is_flag=True, required=False, help='display raw data' )
@argument('filters', nargs=-1)
def show( filters, frmt, raw ):
	show_activity( gc.db.find( filters, include_grouped=True ), frmt=frmt, display_raw=raw )

@cli.command( help='groups activities' )
@option( '-r', '--revert', is_flag=True, required=False, help='splits up groups and creates separate activities again' )
@argument( 'filters', nargs=-1 )
def group( filters, revert: bool ):
	if revert:
		ungroup_activities( gc.db.find( filters ), cfg['force'].get() )
	else:
		group_activities( gc.db.find( filters, True, False, True ), cfg['force'].get() )

@cli.command( hidden=True, help='groups activities to multipart activities' )
@option( '-r', '--revert', is_flag=True, required=False, help='splits up multipart groups and creates separate activities again' )
@argument( 'filters', nargs=-1 )
def part( filters, revert: bool ):
	if revert:
		unpart_activities( gc.db.find( filters ), cfg['force'].get() )
	else:
		part_activities( gc.db.find( filters, True, False, True ), cfg['force'].get() )

@cli.command( hidden=True, help='edits activities' )
@argument( 'filters', nargs=-1 )
def edit( identifier ):
	edit_activities( [Application.instance().db.find_by_id( identifier )] )

@cli.command( help='renames activities' )
@argument( 'filters', nargs=-1 )
def rename( filters ):
	rename_activities( gc.db.find( filters, True, False, True ) )

@cli.command( help='reimports activities' )
@argument( 'filters', nargs=-1 )
def reimport( filters ):
	_db = Application.instance().db
	_force = Application.instance().cfg['force'].get( False )
	reimport_activities( _db.find( filters ), _db, _force )

@cli.command( help='export activities' )
@option( '-f', '--format', 'fmt', required=True, type=Choice( ['csv', 'geojson', 'gpx', 'kml', 'shp'], case_sensitive=False ), metavar='FORMAT' )
@option( '-o', '--output', required=False, type=ClickPath(), metavar='PATH' )
@argument( 'filters', nargs=-1 )
def export( fmt: str, output: str, filters ):
	app = Application.instance()
	if not output:
		output = prompt( "Enter path to output file" )

	activities = app.db.find( filters )
	if fmt == 'csv':
		export_csv( activities, Path( output ) )
	elif fmt == 'geojson':
		export_geojson( activities, Path( output ) )
	elif fmt == 'gpx':
		export_gpx( activities, Path( output ) )
	elif fmt == 'kml':
		export_kml( activities, output )
	elif fmt == 'shp':
		export_shp( activities, output )

@cli.command( help='application setup' )
def setup():
	setup_application()

@cli.command( hidden=True, help='For testing plugin system' )
def init():
	from .plugins import load as load_plugins
	load_plugins()

@cli.command( hidden=True, help='inspects activities' )
@option( '-t', '--table', is_flag=True, required=False, help='displays fields in a table-like manner' )
@argument( 'filters', nargs=-1 )
def inspect( filters, table ):
	inspect_activities( gc.db.find( filters, True, True, True ), display_table=table )

@cli.command( hidden=True, help='Performs some validation and sanity tasks.' )
@argument( 'filters', nargs=-1 )
def validate( filters ):
	validate_activities( gc.db.find( filters, True, True, True ) )

@cli.command( help='Displays the version number and exits.' )
def version():
	echo( '0.1.0' )

def main( args=None ):
	cli()  # trigger cli

def _init_logging( debug: bool = False ):
	console_handler = StreamHandler( stderr )
	if debug:
		console_handler.setLevel( DEBUG )
	else:
		console_handler.setLevel( INFO )
	console_handler.setFormatter( Formatter( '%(message)s' ) )

	root_logger = getLogger( __package__ )
	if debug:
		root_logger.setLevel( DEBUG )
	else:
		root_logger.setLevel( INFO )
	root_logger.addHandler( console_handler )

if __name__ == '__main__':
	log.debug( "running __main__ in cli" )
	main()

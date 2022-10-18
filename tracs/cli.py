
from datetime import datetime
from logging import DEBUG
from logging import INFO
from logging import Formatter
from logging import StreamHandler
from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import List

from click import argument
from click import echo
from click import option
from click import pass_context
from click import pass_obj
from click import Choice
from click import Path as ClickPath
from click_shell import shell

from tracs.edit import equip_activities
from tracs.edit import modify_activities
from tracs.edit import tag_activities
from tracs.edit import unequip_activities
from tracs.edit import untag_activities
from tracs.inout import export_activities
from tracs.inout import export_resources
from tracs.inout import import_activities
from tracs.inout import open_activities
from tracs.list import inspect_registry
from tracs.list import inspect_resources
from .activity import Activity
from .application import Application
from .config import ApplicationContext
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
from .inout import reimport_activities
from .list import inspect_activities
from .list import list_activities
from .list import show_fields
from .show import show_activity
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
@shell( prompt=f'{APPNAME} > ', intro=f'Starting interactive shell mode, enter <exit> to leave this mode again, use <{APPNAME} --help> for help ...' )
@option( '-c', '--configuration', is_flag=False, required=False, help='configuration area location', metavar='PATH' )
@option( '-l', '--library', is_flag=False, required=False, help='library location', metavar='PATH' )
@option( '-v', '--verbose', is_flag=True, default=None, required=False, help='be more verbose when logging' )
@option( '-d', '--debug', is_flag=True, default=None, required=False, help='enable output of debug messages' )
@option( '-f', '--force', is_flag=True, default=None, required=False, help='forces operations to be carried out' )
@option( '-p', '--pretend', is_flag=True, default=None, required=False, help='pretends to work, only simulates everything and does not persist any changes' )
@pass_context
def cli( ctx, configuration, debug, force, library, verbose, pretend ):
	# create application context object
	ctx.obj = ApplicationContext()

	_init_logging( debug )

	if debug:
		getLogger( __package__ ).setLevel( DEBUG )
		getLogger( __package__ ).handlers[0].setLevel( DEBUG ) # this should not fail as the handler is defined in __main__

	log.debug( f'triggered CLI with flags debug={debug}, verbose={verbose}, force={force}, pretend={pretend}' )

	gc.app = Application.instance(
		ctx=ctx.obj,
		config_dir=Path( configuration ) if configuration else None,
		lib_dir=Path( library ) if library else None,
		verbose=verbose,
		debug=debug,
		force=force,
		pretend=pretend
	)

	# todo: move this init to application module
	ctx.obj.instance = gc.app
	ctx.obj.db = gc.app.db
	ctx.obj.db_file = gc.app.db.db_path
	ctx.obj.meta = gc.app.db.metadata

	migrate_application( ctx.obj, None ) # check if migration is necessary

@cli.command( hidden=True )
@option( '-b', '--backup', is_flag=True, required=False, help='creates a backup of the internal database' )
@option( '-f', '--fields', is_flag=True, required=False, hidden=True, help='shows available fields, which can be used for queries (EXPERIMENTAL!)' )
@option( '-m', '--migrate', is_flag=False, required=False, type=str, help='performs a database migration', metavar='FUNCTION' )
@option( '-r', '--restore', is_flag=True, required=False, help='restores the last version of the database from the backup' )
@option( '-s', '--status', is_flag=True, required=False, help='prints some db status information' )
@pass_obj
def db( ctx: ApplicationContext, backup: bool, fields: bool, migrate: str, restore: bool, status: bool ):
	app = Application.instance()
	if backup:
		backup_db( app.db_file, app.backup_dir )
	elif fields:
		show_fields()
	elif migrate:
		migrate_application( ctx, function_name=migrate, force=ctx.force )
	elif restore:
		restore_db( app.db.db, app.db_file, app.backup_dir, app.cfg['force'].get() )
	elif status:
		status_db( ctx.db )

@cli.command( help='prints the current configuration' )
@pass_obj
def config( ctx: ApplicationContext ):
	show_config( ctx )

@cli.command( help='prints information about fields that can be used for filtering' )
def fields():
	show_fields()

@cli.command( 'import', hidden=True, help='imports activities' )
@option( '-a', '--as-one', required=False, is_flag=True, help='multiple resources will be imported as one single activity (dangerous!)' )
@option( '-d', '--skip-download', required=False, is_flag=True, help='skips download of activities' )
@option( '-i', '--importer', required=False, help='importer to use (default is auto)' )
@option( '-m', '--move', required=False, is_flag=True, help='move resources (dangerous, input files will be removed)' )
@argument( 'sources', nargs=-1 )
@pass_context
def imprt( ctx, sources, skip_download: bool = False, importer = 'auto', as_one: bool = False, move: bool = False ):
	import_activities( ctx.obj, sources=sources, skip_download=skip_download, importer=importer, as_one=as_one, move=move )

@cli.command( help='fetches activity ids' )
@argument( 'sources', nargs=-1 )
@pass_context
def fetch( ctx, sources: List[str] ):
	# fetch from all sources if no sources are provided
	sources = sources or Registry.service_names()
	for s in sources:
		if s in Registry.service_names():
			service = Registry.services.get( s )
			service.import_activities( ctx=ctx.obj, force=ctx.obj.force, pretend=ctx.obj.pretend, skip_download=True )
		else:
			log.error( f'unable to fetch from service {s}: no such service' )

@cli.command( help='downloads activities' )
@argument( 'filters', nargs=-1 )
@pass_context
def download( ctx, filters ):
	download_activities( ctx.obj.db.find( filters or [] ), force=ctx.obj.force, pretend=ctx.obj.pretend )

@cli.command( help='creates links for downloaded resources of activities' )
@option( '-a', '--all', 'all_', is_flag=True, required=False, help='creates links for all activities (instead of recent ones only), overriding provided filters' )
@argument( 'filters', nargs=-1 )
@pass_context
def link( ctx, all_, filters ):
	filters = [] if all_ else filters
	link_activities( ctx.obj.db.find( filters ), force=ctx.obj.force, pretend=ctx.obj.pretend )

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
@option( '-s', '--sort', is_flag=False, required=False, help='sorts the output according to an attribute' )
@option( '-r', '--reverse', is_flag=True, required=False, help='reverses sort order' )
@option( '-f', '--format', 'format_name', is_flag=False, required=False, type=str, hidden=True, help='uses the format with the provided name when printing', metavar='FORMAT' )
@argument('filters', nargs=-1)
@pass_context
def ls( ctx, sort, reverse, format_name, filters ):
	list_activities( list( ctx.obj.db.find( filters ) ), sort, reverse, format_name )

@cli.command( help='shows details about activities and resources' )
#@option( '-f', '--format', 'frmt', is_flag=False, required=False, type=str, hidden=True, help='uses the provided format string when printing', metavar='FORMAT' )
@option( '-r', '--raw', is_flag=True, required=False, help='display raw data' )
@argument('filters', nargs=-1)
@pass_context
def show( ctx, filters, raw ):
	show_activity( ctx.obj.db.find( filters ), ctx=ctx.obj, display_raw=raw, verbose=ctx.obj.verbose )

@cli.command( help='groups activities' )
@argument( 'filters', nargs=-1 )
@pass_obj
def group( ctx: ApplicationContext, filters: List[str] ):
	group_activities( ctx, list( ctx.db.find( filters ) ), force=ctx.force, pretend=ctx.pretend )

@cli.command( help='reverts activity groupings' )
@argument( 'filters', nargs=-1 )
@pass_obj
def ungroup( ctx: ApplicationContext, filters: List[str] ):
	ungroup_activities( ctx, ctx.db.find( filters ), force=ctx.force, pretend=ctx.pretend )

@cli.command( hidden=True, help='groups activities to multipart activities' )
@argument( 'filters', nargs=-1 )
@pass_obj
def part( ctx: ApplicationContext, filters: List[str] ):
	part_activities( ctx.db.find( filters ), force=ctx.force, pretend=ctx.pretend )

@cli.command( hidden=True, help='reverts multipart activities' )
@argument( 'filters', nargs=-1 )
@pass_obj
def unpart( ctx: ApplicationContext, filters: List[str] ):
	unpart_activities( ctx.db.find( filters ), force=ctx.force, pretend=ctx.pretend )

@cli.command( help='modifies activities' )
@option( '-f', '--field', is_flag=False, required=True, help='field to modify' )
@option( '-v', '--value', is_flag=False, required=True, help='new field value' )
@argument( 'filters', nargs=-1 )
@pass_context
def modify( ctx, filters, field, value ):
	modify_activities( activities=ctx.obj.db.find( filters ), field=field, value=value, ctx = ctx.obj, force=ctx.obj.force, pretend=ctx.obj.pretend )

@cli.command( hidden=True, help='edits activities' )
@argument( 'filters', nargs=-1 )
def edit( identifier ):
	edit_activities( [Application.instance().db.find_by_id( identifier )] )

@cli.command( help='renames activities' )
@argument( 'filters', nargs=-1 )
@pass_obj
def rename( ctx: ApplicationContext, filters: str ):
	rename_activities( list( ctx.db.find( filters ) ), ctx, ctx.force, ctx.pretend )

@cli.command( help='reimports activities' )
@option( '-r', '--recordings', is_flag=True, required=False, help='includes data from GPX, TCX etc. for reimporting' )
@option( '-o', '--offset', is_flag=False, required=False, help='offset for correcting value for time' )
@option( '-tz', '--timezone', is_flag=False, required=False, help='timezone for calculating value for local time' )
@argument( 'filters', nargs=-1 )
@pass_obj
def reimport( ctx: ApplicationContext, filters, recordings: bool = False, offset: str = None, timezone: str = None ):
	reimport_activities( list( ctx.db.find( filters ) ), include_recordings=recordings, offset=offset, timezone=timezone, ctx=ctx )

@cli.command( 'open', help='opens activities in an external application' )
@argument( 'filters', nargs=-1 )
@pass_context
def open_cmd( ctx, filters ):
	open_activities( list( ctx.obj.db.find( filters ) ), ctx.obj.db )

@cli.command( help='export activities/resources (experimental)' )
@option( '-f', '--format', 'fmt', required=False, type=Choice( ['csv', 'geojson', 'gpx', 'kml', 'shp'], case_sensitive=False ), metavar='FORMAT' )
@option( '-g', '--aggregate', required=False, is_flag=True )
@option( '-l', '--overlay', required=False, is_flag=True, hidden=True )
@option( '-o', '--output', required=False, type=ClickPath(), metavar='PATH' )
@option( '-r', '--resource', required=False, is_flag=True )
@option( '-t', '--type', required=False, is_flag=False )
@argument( 'filters', nargs=-1 )
@pass_obj
def export( ctx: ApplicationContext, fmt: str, output: str, aggregate: bool, overlay: bool, resource: bool, type: str, filters: List[str] ):
	if resource:
		export_resources( ctx.db.find_resources( filters ) )
	else:
		export_activities( ctx.db.find( filters ), type=type, force=ctx.force, pretend=ctx.pretend )

@cli.command( 'set', hidden=True, help='sets field values manually' )
@argument( 'filters', nargs=-1 )
def set_cmd( filters ):
	pass

@cli.command( hidden=True, help='unsets field values' )
@argument( 'filters', nargs=-1 )
def unset( filters ):
	pass

@cli.command( help='Tags activities' )
@option( '-t', '--tag', is_flag=False, required=True, multiple=True, help='tag to add to an activity' )
@argument( 'filters', nargs=-1 )
@pass_obj
def tag( ctx: ApplicationContext, filters, tag ):
	tag_activities( list( ctx.db.find( filters ) ), tags=tag, ctx=ctx )

@cli.command( help='Removes tags from activities' )
@option( '-t', '--tag', is_flag=False, required=True, multiple=True, help='tag to remove from an activity' )
@argument( 'filters', nargs=-1 )
@pass_obj
def untag( ctx: ApplicationContext, filters, tag ):
	untag_activities( list( ctx.db.find( filters ) ), tags=tag, ctx=ctx )

@cli.command( help='Add equipment to an activity' )
@option( '-e', '--equipment', is_flag=False, required=True, multiple=True, help='equipment to add to an activity' )
@argument( 'filters', nargs=-1 )
@pass_obj
def equip( ctx: ApplicationContext, filters, equipment ):
	equip_activities( list( ctx.db.find( filters ) ), equipment=equipment, ctx=ctx )

@cli.command( help='Removes equipment from activities' )
@option( '-e', '--equipment', is_flag=False, required=True, multiple=True, help='equipment to remove from an activity' )
@argument( 'filters', nargs=-1 )
@pass_obj
def unequip( ctx: ApplicationContext, filters, equipment ):
	unequip_activities( list( ctx.db.find( filters ) ), equipment=equipment, ctx=ctx )

@cli.command( help='application setup' )
def setup():
	setup_application()

@cli.command( hidden=True, help='For testing plugin system' )
def init():
	from .plugins import load as load_plugins
	load_plugins()

@cli.command( hidden=True, help='inspects activities/resources/internal registry' )
@option( '-g', '--registry', is_flag=True, required=False, help='inspects the internal registry, filter will be ignored' )
@option( '-r', '--resource', is_flag=True, required=False, help='applies the provided filters to resources instead of activities' )
@argument( 'filters', nargs=-1 )
@pass_obj
def inspect( ctx: ApplicationContext, filters, registry: bool, resource: bool ):
	if registry:
		inspect_registry()
	elif resource:
		inspect_resources()
	else:
		inspect_activities( ctx.db.find( filters ) )

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

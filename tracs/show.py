
from dataclasses import fields
from logging import getLogger
from typing import List

from rich import box
from rich.columns import Columns
from rich.pretty import Pretty as pp
from rich.table import Table

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.config import ApplicationContext, console
from tracs.registry import Registry
from tracs.resources import Resource
from tracs.service import Service
from tracs.uid import UID
from tracs.utils import fmt

log = getLogger( __name__ )

TITLE_STYLE = { 'title_justify': 'left', 'title_style': 'bold bright_blue' }

def show_resources( activities: List[Activity], ctx: ApplicationContext, display_raw: bool = False, verbose: bool = True, format_name: str = None ) -> None:
	for a in activities:
		for r in ctx.db.find_resources_by_uids( a.uids ):
			table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title=f'Resource:', **TITLE_STYLE )
			for f in sorted( Resource.fieldnames() ):
				if f in ['__parent_activity__', 'content', 'raw']:
					continue
				table.add_row( f, pp( getattr( r, f ) ) )

			table.add_row( '[bright_blue]native fields[/bright_blue]', '' )
			try:
				act = Registry.importer_for( r.type ).load_as_activity( path=Service.path_for_resource( r ) )
				for nf in fields( act ):
					table.add_row( nf.name, pp( getattr( act, nf.name ), max_depth=1, no_wrap=True ) )
			except AttributeError:
				table.add_row( '...', '[red]error: failed to load resource as activity[/red]' )

			console.print( table )

def show_activities( activities: [Activity], ctx: ApplicationContext, display_raw: bool = False, format_name: str = None, verbose: bool = False ) -> None:
	if format_name == 'all':
		show_fields = [ f.name for f in Activity.fields() ]
		show_fields.sort()
	else:
		show_fields = ctx.config.formats.show.get( format_name, ctx.config.formats.show.default ).split()

	for a in activities:
		if display_raw:
			show_raw_activity( a, ctx )
		else:
			if verbose:
				show_verbose_activity( a, ctx, show_fields )
			else:
				show_activity( a, ctx, show_fields )

def show_raw_activity( a: Activity, ctx: ApplicationContext ):

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title='Fields and Values:', **TITLE_STYLE )
	table.add_row( '[blue]field[/blue]', '[blue]value[/blue]' )
	for f in sorted( Activity.fields(), key=lambda field: field.name ):
		table.add_row( f.name, pp( getattr( a, f.name ) ) )
	console.print( table )

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title='Resources:', **TITLE_STYLE )
	table.add_row( '[blue]id[/blue]', '[blue]name[/blue]', '[blue]path[/blue]', '[blue]exists[/blue]', '[blue]type[/blue]', '[blue]uid[/blue]', '[blue]status[/blue]', '[blue]source[/blue]' )
	for uid in a.uids:
		resources = ctx.db.find_resources( uid )
		for r in resources:
			resource_path = Registry.services.get( r.classifier ).path_for( resource=r )
			path_exists = '[bright_green]\u2713[/bright_green]' if resource_path.exists() else '[bright_red]\u2716[/bright_red]'
			table.add_row( pp( r.id ), r.name, r.path, path_exists, r.type, r.uid, pp( r.status ), r.source )
	console.print( table )

def show_activity( a: Activity, ctx: ApplicationContext, show_fields: List[str] ):
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	rows = [[field, getattr( a, field )] for field in show_fields]

	for row in rows:
		if row[1] is not None and row[1] != '' and row[1] != [] and row[1] != { }:
			table.add_row( row[0], fmt( row[1] ) )

	console.print( table )
	# console.print( '\u00b9 Proper timezone support is currently missing, local timezone is displayed' )

def show_verbose_activity( a: Activity, ctx: ApplicationContext, show_fields: List[str] ) -> None:
	# activity data
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title='Activity Data:', **TITLE_STYLE )
	rows = [[field, getattr( a, field )] for field in show_fields]
	for row in rows:
		if row[1] is not None and row[1] != '' and row[1] != [] and row[1] != { }:
			table.add_row( row[0], fmt( row[1] ) )
	console.print( table )

	# locations/urls
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title='URLs and Locations:', **TITLE_STYLE )
	uids = a.metadata.members if a.group else [ a.uid ]
	for uid in uids:
		uid = UID( uid ) if isinstance( uid, str ) else uid
		table.add_row( uid.classifier, Service.url_for_uid( str( uid )  ) )
	for r in a.resources:
		table.add_row( 'local db', ctx.db_fs.getsyspath( r.path ) )
	console.print( table )

	# attached resources
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False, title='Resources:', **TITLE_STYLE )
	table.add_row( '[blue]path[/blue]', '[blue]absolute path[/blue]', '[blue]type[/blue]', '[blue]exists[/blue]', '[blue]overlayed[/blue]' )
	for r in a.resources:
		resource_path = ctx.db_fs.getsyspath( r.path )
		resource_path_exists = '[bright_green]\u2713[/bright_green]' if ctx.db_fs.exists( r.path ) else '[bright_red]\u2716[/bright_red]'

		# overlay_sign = ' \u29c9'
		# overlay_sign = '\u2a39'
		overlay_sign = '\u2a01'
		overlay_exists = f'[bright_green] {overlay_sign}[/bright_green]' if ctx.overlay_fs.exists( r.path ) else '[bright_red]\u2716[/bright_red]'

		table.add_row( r.path, resource_path, r.type, resource_path_exists, overlay_exists )

	# resource_url = Registry.services.get( r.classifier ).url_for( resource=r )
	# table.add_row( pp( r.doc_id ), f'{r.path} {path_exists}{overlay_path_exists}', absolute_path, r.type, resource_url )

	console.print( table )

def show_aggregate( activities: [Activity], ctx: ApplicationContext ) -> None:
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )

	aggregate = Activity( other_parts=activities )

	table.add_row( *[ 'count', fmt( len( activities ) ) ] )
	table.add_row( *[ 'distance', fmt( aggregate.distance ) ] )
	table.add_row( *[ 'duration', fmt( aggregate.duration ) ] )

	console.print( table )

def show_keywords( ctx: ApplicationContext ) -> None:
	keywords = sorted( ctx.registry.keywords.keys() )
	if ctx.verbose:
		table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
		[ table.add_column( f'[blue]{c}[/blue]' ) for c in [ 'keyword', 'description' ] ]
		[ table.add_row( k, ctx.registry.keywords[k].description ) for k in keywords ]
		ctx.console.print( table )
	else:
		ctx.console.print( Columns( keywords, padding=(0, 4), equal=True, column_first=True ) )

def show_equipments( ctx: ApplicationContext ) -> None:
	all_equipments = sorted( set().union( *[a.equipment for a in ctx.db.activities] ) )
	ctx.console.print( Columns( all_equipments, padding=(0, 4), equal=True, column_first=True ) )

def show_tags( ctx: ApplicationContext ) -> None:
	all_tags = sorted( set().union( *[a.tags for a in ctx.db.activities] ) )
	ctx.console.print( Columns( all_tags, padding=(0, 4), equal=True, column_first=True ) )

def show_types( ctx: ApplicationContext, used_only: bool = False ) -> None:
	if used_only:
		all_type_names = sorted( set( [ a.type.name for a in ctx.db.activities if a.type is not None ] ) )
	else:
		all_type_names = sorted( ActivityTypes.names() )
	
	title = '[blue bold]Activity Types:[/blue bold] [green]value[/green] (display name)'
	types = [f'[green]{t}[/green] ({ActivityTypes.get( t ).display_name})' for t in all_type_names ]
	ctx.console.print( Columns( types, padding=(0, 4), equal=True, column_first=True, title=title ) )


from logging import getLogger
from re import split
from typing import List, Optional

from dynaconf import inspect_settings
from dynaconf.vendor.box.exceptions import BoxKeyError
from rich import box
from rich.pretty import Pretty, Pretty as pp
from rich.table import Table

from tracs.activity import Activity
from tracs.context import ApplicationContext
from tracs.core import fields_of
from tracs.ui import CONSOLE as console, print_kvtable
from tracs.ui.tables import create_table
from tracs.ui.utils import yellow
from tracs.utils import red

log = getLogger( __name__ )

DEFAULT_SORT_FIELD = 'starttime'
DEFAULT_LIST_FORMAT = 'default'

# noinspection PyTestUnpassedFixture
def list_activities( activities: List[Activity], sort: Optional[str] = None,
                     reverse: bool = False, format_name: Optional[str] = None,
                     fields: Optional[str] = None, ctx: Optional[ApplicationContext] = None ) -> None:

	sort = sort or DEFAULT_SORT_FIELD
	fields = fields or []

	try:
		activities = sorted( activities, key=lambda act: ( ( att := getattr( act, sort, None ) ) is None, att ) )
	except (AttributeError, TypeError):
		log.warning( f'unable to sort for field "{sort}", falling back to "{DEFAULT_SORT_FIELD}"' )
		activities = sorted( activities, key=lambda act: getattr( act, DEFAULT_SORT_FIELD ) )

	if reverse:
		activities.reverse()

	if fields:
		list_fields = fields.split()

	elif format_name:
		try:
			list_fields = ctx.config.formats.list[format_name].split()
		except BoxKeyError:
			list_fields = ctx.config.formats.list[DEFAULT_LIST_FORMAT].split()

	else:
		list_fields = ctx.config.formats.list[DEFAULT_LIST_FORMAT].split()

	table = create_table(
		box_name=ctx.config.formats.table.box,
		headers=[ f for f in list_fields ],
		rows=[ list( a.format( *list_fields ) ) for a in activities ],
	)

	if len( table.rows ) > 0:
		console.print( table )

def show_filters( ctx: ApplicationContext ):
	console.print( create_table(
		[ 'filter', 'expression' ],
		sorted( ctx.config.filters.to_dict().items(), key=lambda flt: flt[0] ),
		'MINIMAL'
	) )

def show_fields():
	table = Table( box=box.MINIMAL, show_header=True, show_footer=False )
	table.caption, table.caption_justify = 'Derived fields are marked with \u24b9  and shown in yellow.', 'left'
	table.add_column( '', justify='center' )
	table.add_column( 'field' )
	table.add_column( 'type' )

	for f in sorted( fields_of( Activity ), key=lambda fld: fld.name ):
		derived = yellow( '\u24b9' ) if f.metadata.get( 'derived' ) else ''
		name = f'[yellow]{f.name}[/yellow]' if f.metadata.get( 'derived' ) else f.name
		table.add_row( derived, name, pp( f.type ) )

	console.print( table )

def show_config( ctx: ApplicationContext ):
	print_kvtable(
		[
			( 'configuration area', ctx.config_dir ),
			( 'configuration file', ctx.config_file ),
			( 'appstate file', ctx.state_file ),
			( 'library', ctx.lib_dir ),
			( 'database', ctx.db_dir ),
			( 'takeouts', ctx.takeouts_dir ),
			( 'overlay', ctx.overlay_dir ),
			( 'var', ctx.var_dir ),
			( 'backups', ctx.backup_dir ),
			( 'temp', ctx.tmp_fs.getsyspath( '/' ) ),
		],
		title='Working directories:',
	)

	#print_dict( dict( inspect_settings( ctx.config ).get( 'current' ) ) )
	console.print( 'Configuration:', style='bold' )
	console.print( Pretty( inspect_settings( ctx.config ).get( 'current' ), max_string=40, overflow='ellipsis' ) )

	console.print( 'State:', style='bold' )
	console.print( Pretty( inspect_settings( ctx.state ).get( 'current' ), max_string=40, overflow='ellipsis' ) )

def shorten( s: str ) -> str:
	max_length = 120
	if len( str( s ) ) > max_length:
		start = int( max_length / 2 )
		end = int( len( str( s ) ) - (max_length / 2) )
		return f"{str( s )[:start]}{red('... ...')}{str( s )[end:]}"
	else:
		return s

def _type( o ) -> str:
	s = split( '^<.+\'(.+)\'>$', str( type( o ) ) )
	return s[1] if len( s ) > 2 else str( type( o ) )

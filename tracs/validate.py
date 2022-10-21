
from sys import modules
from typing import List

from click import style
from logging import getLogger
from rich import box
from rich.table import Table

from .activity import Activity
from .config import ApplicationContext
from .config import console
from .service import Service

log = getLogger( __name__ )

ERROR = style('Error', fg='red')
WARN = style('Warning', fg='yellow')
INFO = style('Info', fg='green')

def validate_activities( activities: List[Activity], function: str, ctx: ApplicationContext ) -> None:
	report: List[List] = []

	if function:
		function_name = f'{function}'
		if function_name in dir( modules[ __name__ ] ):
			if fn := getattr( modules[ __name__ ], function_name ):
				report_data = fn( activities, ctx )
				report.append( [function_name, report_data] )
		else:
			log.error( f'skipping validation: unable to find function {function_name}' )

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( '', f'[bold bright_blue]Validation Report:[/bold bright_blue]', '' )
	table.add_section()
	for r in report:
		table.add_row( '', f'[blue]{r[0]}[/blue]', '' )
		table.add_section()
		for line in r[1]:
			table.add_row( *line )

	console.print( table )

def check_gpx_resources( activities: List[Activity], ctx: ApplicationContext ) -> List[List[str]]:
	report_data = []
	all_resources = ctx.db.resources.all()
	ctx.start( 'Checking for file existance', total=len( all_resources ) )

	for r in all_resources:
		ctx.advance( msg=r.path )

		if not r.path.endswith( '.gpx' ):
			continue

		path = Service.path_for_resource( r )
		if not path.exists():
			if r.status == 200:
				_error( report_data, 'missing file, but marked as available in db', str( path ) )
			else:
				_warn( report_data, f'missing file, resource status = {r.status}', str( path ) )

		if ctx.verbose:
			_info( report_data, 'file ok', str( path ) )

	ctx.complete()

	return report_data

# --- helper ---

def _info( report_data: List, issue = '', details = '' ):
	report_data.append( ['[bright_green]\u2714[/bright_green]', issue, details] )

def _warn( report_data: List, issue = '', details = '' ):
	data = [ f'[yellow]{s}[/yellow]' for s in [ '\u229a', issue ] ]
	data.append( details )
	report_data.append( data )

def _error( report_data: List, issue = '', details = '' ):
	report_data.append( [ f'[bright_red]{s}[/bright_red]' for s in [ '\u2718', issue, details ] ] )

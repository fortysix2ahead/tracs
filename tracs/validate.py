
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

def resource_files( activities: List[Activity], ctx: ApplicationContext ) -> List[List[str]]:
	report_data = []
	all_resources = ctx.db.resources.all()
	ctx.start( 'Checking resource files ...', total=len( all_resources ) )

	for r in all_resources:
		ctx.advance( msg=r.path )

		path = Service.path_for_resource( r )

		if path.exists():
			if r.status == 200:
				_info( report_data, 'file ok', str( path ), ctx )
			else:
				_error( report_data, f'file exists, but is marked with status = {r.status}', str( path ), ctx )

		else:
			if r.status == 200:
				_error( report_data, f'missing file, but marked with resource status = {r.status}', str( path ), ctx )
			elif r.status == 404:
				_info( report_data, 'file missing (404)', str( path ), ctx )
			else:
				_warn( report_data, f'missing file, resource status = {r.status}', str( path ), ctx )

	ctx.complete()

	return report_data

def tcx_files( activities: List[Activity], ctx: ApplicationContext ) -> List[List[str]]:
	from tcxreader.tcxreader import TCXReader
	from tcxreader.tcx_exercise import TCXExercise
	from xml.etree.ElementTree import ParseError

	report_data = []
	all_resources = ctx.db.resources.all()
	ctx.start( 'Checking resource files ...', total=len( all_resources ) )

	reader = TCXReader()

	for r in all_resources:
		ctx.advance( msg=r.path )

		if not r.path.endswith( '.tcx' ):
			continue

		if (path := Service.path_for_resource( r )).exists():

			try:
				exercise: TCXExercise = reader.read( str( path ) )
				_info( report_data, f'TCX parsing ok ({len( exercise.trackpoints )})', str( path ), ctx )
			except ParseError:
				_error( report_data, f'TCX parse error', str( path ), ctx )

	ctx.complete()
	return report_data

# --- helper ---

def _info( report_data: List, issue = '', details = '', ctx = None ):
	if ctx.debug:
		report_data.append( ['[bright_green]\u2714[/bright_green]', issue, details] )

def _warn( report_data: List, issue = '', details = '', ctx = None ):
	data = [ f'[yellow]{s}[/yellow]' for s in [ '\u229a', issue ] ]
	data.append( details )
	report_data.append( data )

def _error( report_data: List, issue = '', details = '', ctx = None ):
	report_data.append( [ f'[bright_red]{s}[/bright_red]' for s in [ '\u2718', issue, details ] ] )

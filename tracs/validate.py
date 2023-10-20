
from logging import getLogger
from pathlib import Path
from sys import modules
from typing import ClassVar, List

from attrs import define, field
from rich import box
from rich.table import Table

from tracs.activity import Activity
from tracs.config import ApplicationContext, console
from tracs.service import Service

log = getLogger( __name__ )

ERROR = 'ERROR'
WARNING = 'WARNING'
INFO = 'INFO'

@define
class ReportItem:

	status: str = field( default=ERROR )
	issue: str = field( default=None )
	details: str = field( default=None )
	path: Path = field( default=None )
	correction: bool = field( default=False )

	def as_list( self ) -> List[str]:
		columns = []
		if self.status == ERROR:
			columns.append( '[bright_red]\u2718[/bright_red]' )
			if self.correction:
				columns.append( '[bright_green]\u2714[/bright_green]' )
			else:
				columns.append( '[bright_red]\u2718[/bright_red]' )

			columns.append( f'[bright_red]{self.issue}[/bright_red]' )
			if self.details:
				columns.append( f'[bright_red]{self.details}[/bright_red]' )
			elif self.path:
				columns.append( f'[bright_red]{self.path}[/bright_red]' )
			else:
				columns.append( f'' )

		elif self.status == WARNING:
			columns.append( '[yellow]\u229a[/yellow]' )
			if self.correction:
				columns.append( '[bright_green]\u2714[/bright_green]' )
			else:
				columns.append( '[yellow]\u2718[/yellow]' )

			columns.append( f'[yellow]{self.issue}[/yellow]' )
			if self.details:
				columns.append( f'[yellow]{self.details}[/yellow]' )
			elif self.path:
				columns.append( f'[yellow]{self.path}[/yellow]' )
			else:
				columns.append( f'' )

		elif self.status == INFO:
			columns.append( '[bright_green]\u2714[/bright_green]' )
			columns.append( '[bright_green]\u207F/\u2090[/bright_green]' )
			columns.append( f'{self.issue}' )
			if self.details:
				columns.append( f'{self.details}' )
			elif self.path:
				columns.append( f'{self.path}' )
			else:
				columns.append( f'' )

		return columns

@define
class ReportData:

	ctx: ClassVar[ApplicationContext] = None

	name: str = field( default=None )
	items: List[ReportItem] = field( factory=list )

	def info( self, issue, details = None, path = None ):
		self.items.append( ReportItem( status=INFO, issue=issue, details=details, path=path ) )

	def warn( self, issue, details = None, path = None ):
		self.items.append( ReportItem( status=WARNING, issue=issue, details=details, path=path ) )

	def error( self, issue, details = None, path = None ):
		self.items.append( ReportItem( status=ERROR, issue=issue, details=details, path=path ) )

	def as_list( self ) -> List[List[str]]:
		item_list = []
		for item in self.items:
			if item.status != INFO or ReportData.ctx.debug:
				item_list.append( item.as_list() )
		return item_list

def validate_activities( activities: List[Activity], function: str, correct: bool, ctx: ApplicationContext ) -> None:
	ReportData.ctx = ctx
	report: List[ReportData] = []

	if function:
		function_name = f'{function}'
		if function_name in dir( modules[ __name__ ] ):
			if fn := getattr( modules[ __name__ ], function_name ):
				report.append( fn( activities, correct ) )
		else:
			log.error( f'skipping validation: unable to find function {function_name}' )

	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	table.add_row( '[bold bright_blue]STA[/bold bright_blue]', '[bold bright_blue]COR[/bold bright_blue]', f'[bold bright_blue]Validation Report:[/bold bright_blue]', '' )
	table.add_section()
	for rd in report:
		table.add_row( '', '', f'[blue]{rd.name}[/blue]', '' )
		table.add_section()
		for l in rd.as_list():
			table.add_row( *l )

	console.print( table )

def resource_files( activities: List[Activity], correct: bool ) -> ReportData:
	rd = ReportData( name='Resource Files' )
	all_resources = ReportData.ctx.db.find_all_resources_for( activities )
	ReportData.ctx.start( 'Checking resource files ...', total=len( all_resources ) )

	for r in all_resources:
		ReportData.ctx.advance( msg=r.path )

		path = Service.path_for_resource( r )

		if path.exists():
			if r.status == 200:
				rd.info( 'file ok', path=path )
			else:
				rd.error( f'file exists, but is marked with status = {r.status}', path=path )

		else:
			if r.status == 200:
				rd.error( f'missing file, but marked with resource status = {r.status}', path=path )
			elif r.status == 404:
				rd.info( 'file missing (404)', path=path )
			else:
				rd.warn( f'missing file, resource status = {r.status}', path=path )

	ReportData.ctx.complete()

	return rd

def tcx_files( activities: List[Activity], correct: bool ) -> ReportData:
	from tcxreader.tcxreader import TCXReader
	from tcxreader.tcx_exercise import TCXExercise
	from xml.etree.ElementTree import ParseError

	rd = ReportData( name='TCX Files' )
	all_resources = ReportData.ctx.db.find_all_resources_for( activities )
	ReportData.ctx.start( 'Checking TCX files for parse errors ...', total=len( all_resources ) )

	reader = TCXReader()

	for r in all_resources:
		ReportData.ctx.advance( msg=str( r.path ) )

		if not r.path.endswith( '.tcx' ):
			continue

		if (path := Service.path_for_resource( r )).exists():
			try:
				exercise: TCXExercise = reader.read( str( path ) )
				rd.info( f'TCX parsing ok ({len( exercise.trackpoints )})', path=path )
			except (ParseError, ValueError) as error:
				rd.error( f'TCX parse error', path=path )

	ReportData.ctx.complete()

	if correct:
		ReportData.ctx.start( 'Repairing TCX files ...', total=len( rd.items ) )

		for item in rd.items:
			ReportData.ctx.advance( msg=str( item.path ) )
			try:
				text = item.path.read_text( encoding='UTF-8' )
#				if match( '^[\s\t]+<\?xml.+\?><TrainingCenterDatabase.+', text ):
				text = text.lstrip()
				item.path.write_text( text, encoding='UTF-8' )
				item.correction = True
			except UnicodeDecodeError:
				item.correction = False

		ReportData.ctx.complete()

	return rd

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

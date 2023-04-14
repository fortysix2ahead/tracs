
from platform import system
from sys import exit as sysexit
from typing import Any
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TextIO
from typing import Tuple
from typing import Union
from typing import overload

from rich.console import Console
from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.prompt import DefaultType
from rich.prompt import Prompt
from rich.prompt import PromptType
from rich.table import Table
from rich.text import Text
from rich.text import TextType

from tracs.utils import colored_diff
from tracs.utils import colored_diff_2
from tracs.utils import fmt
from .config import console as cs

def diff_table( left: Dict, right: Dict, header: Tuple[str, str, str] = None, sort_entries: bool = False ) -> Table:
	table = Table( box=None, show_header=True, show_footer=False )

	field_header = header[0] if header else 'Field'
	left_header = header[1] if header else 'Left'
	right_header = header[2] if header else 'Right'

	table.add_column( field_header, justify="left", no_wrap=True )
	table.add_column( left_header, justify="right", no_wrap=True )
	table.add_column( '', justify="center", no_wrap=True )
	table.add_column( right_header, justify="left", no_wrap=True )

	keys = list( left.keys() | right.keys() )
	if sort_entries:
		keys = sorted( keys )
	show_equals = False

	for k in keys:
		left_str = str( left.get( k ) ) if left.get( k ) is not None else ''
		right_str = str( right.get( k ) ) if right.get( k ) is not None else ''
		if left_str != right_str:
			left_str, right_str = colored_diff( left_str, right_str )
			table.add_row( f'{k}:', left_str, '<->', right_str )
		elif show_equals and left == right:
			table.add_row( k, Pretty( left_str ), '', Pretty( right_str ) )

	return table

def diff_table2( result: Dict, sources: List[Dict], sort_entries: bool = True, show_equals: bool = False ) -> Table:
	table = Table( box=None, show_header=True, show_footer=False )

	field_header = 'Field'
	result_header = 'Value after Grouping'
	source_headers = [ f'Source {i + 1}' for i in range( len( sources ) ) ]

	table.add_column( field_header, justify="left", no_wrap=True )
	table.add_column( result_header, justify="left", no_wrap=True )
	for header in source_headers:
		table.add_column( header, justify="left", no_wrap=True )

	keys = result.keys()
	for source in sources:
		keys = keys | source.keys()
	keys = sorted( list( keys ) ) if sort_entries else list( keys )

	for k in keys:
		row = [ f'{k}', fmt( result.get( k ) ) ]
		for source in sources:
			row.append( fmt( source.get( k ) ) )

		if len( set( row[1:] ) ) > 1 or show_equals:
			for index in range( 2, len( row ) ):
				left, row[index] = colored_diff( row[1], row[index] )

			table.add_row( *row )

	return table

def diff_table_3( sources: List[Dict], result: Dict, sort_entries: bool = True, show_equals: bool = False ) -> Table:
	table = Table( box=None, show_header=True, show_footer=False )

	field_header = '[blue bold]Field[/blue bold]'
	source_headers = [ f'[blue bold]Source {i + 1}[/blue bold]' for i in range( len( sources ) ) ]
	result_header = '[blue bold]Value after Grouping[/blue bold]'

	table.add_column( field_header, justify="left", no_wrap=True )
	for header in source_headers:
		table.add_column( header, justify="left", no_wrap=True )
	table.add_column( result_header, justify="left", no_wrap=True )

	keys = result.keys()
	for source in sources:
		keys = keys | source.keys()
	keys = sorted( list( keys ) ) if sort_entries else list( keys )

	for k in keys:
		src_values, result_value = [ fmt( s.get( k ) ) for s in sources], fmt( result.get( k ) )
		if not show_equals and all( [ src == result_value for src in src_values ] ):
			continue

		# not sure yet, what look best ...

		# row = [ f'[bold]{k}[/bold]', *[ colored_diff( s, result_value )[0] for s in src_values ], result_value ]
		row = [ f'[bold]{k}[/bold]' ]
		for s in src_values:
			# row.append( s if s == result_value else f'[red]{s}[/red]' )
			row.append( s if s == result_value else colored_diff_2( s, result_value )[0] )

		row.append( f'[green]{result_value}[/green]' )
		# row.append( f'{result_value}' )

		table.add_row( *row )

	return table

class Choice( Prompt ):

	FREE_TEXT_OPTION = 'None of the above, enter free text'

	def __init__( self, prompt: TextType = '',
	              *,
	              console: Optional[Console] = None,
	              password: bool = False,
	              headline: str = None,
	              choices: Optional[List[str]] = None,
	              choices_display: Optional[List[str]] = None,
	              show_default: bool = True,
	              show_choices: bool = True,
								use_index: bool = False,
	              allow_free_text: bool ) -> None:

		super().__init__( prompt, console=console, password=password, choices=choices, show_default=show_default, show_choices=show_choices )
		self.headline = headline
		self.choices_display = choices_display
		self.use_index = use_index
		if self.use_index:
			self.choices_display = [ str( index + 1 ) for index in range( len( self.choices ) ) ]
		self.allow_free_text = allow_free_text

	@classmethod
	def ask(
			cls,
			prompt: TextType = "",
			*,
			console: Optional[Console] = None,
			password: bool = False,
			headline: str = None,
			choices: Optional[List[str]] = None,
			choices_display: Optional[List[str]] = None,
			show_default: bool = True,
			show_choices: bool = True,
			use_index: bool = False,
			allow_free_text: bool = False,
			default: Any = ...,
			stream: Optional[TextIO] = None,
	) -> Any:

		_choice = cls(
			prompt,
			console=console,
			password=password,
			headline=headline,
			choices=choices,
			choices_display=choices_display,
			show_default=show_default,
			show_choices=show_choices,
			use_index=use_index,
			allow_free_text=allow_free_text,
		)
		return _choice( default=default, stream=stream )

	def make_prompt( self, default: DefaultType ) -> Text:
		prompt = self.prompt.copy()
		prompt.end = ''

		headline = f'{self.headline}\n' if self.headline else 'choices:\n'
		prompt.append( headline )

		for index in range( len( self.choices ) ):
			if self.choices_display:
				prompt.append( f'  [{self.choices_display[index]}] {self.choices[index]}\n', 'prompt.choices' )
			else:
				prompt.append( f'  {self.choices[index]}\n', 'prompt.choices' )

		prompt.append( 'enter choice' + self.prompt_suffix )
		return prompt

	def process_response( self, value: str ) -> PromptType:

		try:
			value = value.strip()
			if self.choices_display and value in self.choices_display:
				selected_value = self.choices[self.choices_display.index( value )]
			elif not self.choices_display and value in self.choices:
				selected_value = self.choices.index( value )
			elif self.allow_free_text and value != '':
				selected_value = value
			else:
				selected_value = None
		except ValueError:
			selected_value = None

		return selected_value

class InstantConfirm( Confirm ):

	INTERRUPT = '__ctrl_c_interrupt__'

	@classmethod
	def getch_posix( cls ):
		from sys import stdin
		from termios import TCSADRAIN
		from termios import tcgetattr
		from termios import tcsetattr
		from tty import setraw

		fd = stdin.fileno()
		old_settings = tcgetattr( fd )
		try:
			setraw( fd )
			ch = stdin.read( 1 )
		finally:
			tcsetattr( fd, TCSADRAIN, old_settings )
		return ch

	@classmethod
	def getch_windows( cls ):
		from msvcrt import getch
		ch = getch().decode( 'utf-8' )
		return ch

	@classmethod
	def getch( cls ):
		if system() == 'Windows':
			return cls.getch_windows()
		elif system() == 'Linux' or system() == 'Darwin':
			return cls.getch_posix()
		else:
			raise RuntimeError( f'Unsupported System for get character: {system()}' )

	@classmethod
	def get_input( cls, console, prompt: TextType, password: bool, stream: Optional[TextIO] = None ) -> str:
		if prompt:
			cs.print( prompt, end='' )

		if stream:
			result = stream.readline()
		else:
			result = cls.getch()

		return result

	def process_response( self, value: str ):
		if value == '\x03':
			cs.print( '\nAborted ...' )
			sysexit( 0 )

			#return self.INTERRUPT
		else:
			cs.print( '' )
			return super().process_response( value )

def combo():
	from rich.live import Live
	from rich.table import Table
	from rich.console import Group
	from rich.prompt import Prompt

	table = Table( box=None, show_header=False )
	table.add_column( "Row ID" )
	table.add_column( "Description" )

	for row in range( 3 ):
		table.add_row( '>>', f"description {row}" )

	#name = Prompt.ask( "Enter your name" )
	name = InstantConfirm.ask( "Enter your name" )
	group = Group( table, name )

	with Live( table, auto_refresh=False, refresh_per_second=4 ):  # update 4 times a second to feel fluid
		pass

if __name__ == '__main__':
	combo()
#	c = InstantConfirm.ask( "Are you sure?" )
#	print( f'entered: {c}' )


from platform import system
from sys import exit as sysexit
from typing import Dict
from typing import Optional
from typing import TextIO
from typing import Tuple

from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.prompt import DefaultType
from rich.prompt import Prompt
from rich.prompt import PromptType
from rich.table import Table
from rich.text import Text
from rich.text import TextType

from tracs.utils import colored_diff
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

class Choice( Prompt ):

	FREE_TEXT_OPTION = 'None of the above, enter free text'

	def make_prompt( self, default: DefaultType ) -> Text:
		prompt = self.prompt.copy()
		prompt.end = ''

		if self.show_choices and self.choices:
			for index in range( len( self.choices ) ):
				prompt.append( f' [{index + 1}] {self.choices[index]}\n', 'prompt.choices' )
			prompt.append( f' [{len( self.choices ) + 1}] {Choice.FREE_TEXT_OPTION}\n', 'prompt.choices' )
			prompt.append( 'Enter option' )

		prompt.append( self.prompt_suffix )

		return prompt

	def process_response( self, value: str ) -> PromptType:

		try:
			index = int( value.strip() )
			if 0 < index <= len( self.choices ):
				selected_value = self.choices[index - 1]
			elif index == len( self.choices ) + 1:
				selected_value = Choice.FREE_TEXT_OPTION
			else:
				selected_value = ''
		except ValueError:
			selected_value = ''

		return super().process_response( selected_value )

	def check_choice( self, value: str ) -> bool:
		return value in self.choices or value == Choice.FREE_TEXT_OPTION

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

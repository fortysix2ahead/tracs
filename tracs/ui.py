
from platform import system
from sys import exit as sysexit
from typing import Dict
from typing import Optional
from typing import TextIO
from typing import Tuple

from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.table import Table
from rich.text import TextType

from tracs.utils import colored_diff
from .config import console as cs

def diff_table( left: Dict, right: Dict, header: Tuple[str, str, str] = None ) -> Table:
	table = Table( box=None, show_header=True, show_footer=False )

	field_header = header[0] if header else 'Field'
	left_header = header[1] if header else 'Left'
	right_header = header[2] if header else 'Right'

	table.add_column( field_header, justify="left", no_wrap=True )
	table.add_column( left_header, justify="right", no_wrap=True )
	table.add_column( '', justify="center", no_wrap=True )
	table.add_column( right_header, justify="left", no_wrap=True )

	keys = sorted( list( left.keys() | right.keys() ) )
	show_equals = False

	for k in keys:
		left_str = str( left.get( k ) ) if left.get( k ) is not None else ''
		right_str = str( right.get( k ) ) if right.get( k ) is not None else ''
		if left_str != right_str:
			#left_str, right_str = colored_diff( left_str, right_str )
			left_str, right_str = colored_diff( left_str[:20], right_str[:20] )
			table.add_row( f'{k}:', left_str, '<->', right_str )
		elif show_equals and left == right:
			table.add_row( k, Pretty( left_str ), '', Pretty( right_str ) )

	return table

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

if __name__ == '__main__':
	c = InstantConfirm.ask( "Are you sure?" )
	print( f'entered: {c}' )

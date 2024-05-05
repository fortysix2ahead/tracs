from typing import List

from rich import box
from rich.box import Box
from rich.table import Table

DEFAULT_BOX: Box = box.MINIMAL
DEFAULT_HEADER_STYLE = 'blue'
DEFAULT_ROW_STYLES = ['', 'dim']

def create_table( headers: List[str], rows: List[List], box_name: str ):
	table = Table(
		box=create_box( box_name ),
		show_header=True,
		show_footer=False,
		header_style=DEFAULT_HEADER_STYLE,
		row_styles=DEFAULT_ROW_STYLES,
	)

	[ table.add_column( h ) for h in headers ]
	[ table.add_row( *r ) for r in rows ]

	return table


def create_box( name: str ) -> Box:
	try:
		return b if isinstance( b := getattr( box, name.upper() ), Box ) else DEFAULT_BOX
	except AttributeError:
		return DEFAULT_BOX


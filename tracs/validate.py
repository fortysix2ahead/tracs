from typing import List

from click import style
from logging import getLogger
from rich import box
from rich.table import Table

from .activity import Activity
from .activity_types import ActivityTypes as Types
from .config import console
from .config import GlobalConfig as gc
from .service import Service

log = getLogger( __name__ )

ERROR = style('Error', fg='red')
WARN = style('Warning', fg='yellow')
INFO = style('Info', fg='green')

def validate_activities( activities: List[Activity] ) -> None:
	table = Table( box=box.MINIMAL, show_header=False, show_footer=False )
	for a in activities:
		data = []

		_check_missing_type( a, data )
		_check_files( a, data )

		if len( data ) > 0:
			table.add_row( f'activity {a.id} (uid: {a.uid})', '' )
			for d in data:
				table.add_row( d[0], d[1] )

	console.print( table )

def _check_missing_type( a: Activity, data: List[List] ) -> None:
	t = a.get( 'type' )
	type_names = [ entry.name for entry in Types ]
	if t not in type_names:
		data.append( [WARN, f'usage of outdated type {t}' ] )

def _check_files( a: Activity, data: List[List] ) -> None:
	if not a.is_group:
		s: Service = gc.app.services.get( a.service )
		for ext, status in a.get( 'metadata', {} ).items():
			if ext not in [ 'groups' ]:
				if status == 200 and not s.path_for( a, ext ).exists():
					data.append( [WARN, f'file for type {ext} marked with status {status}, but does not exist'] )

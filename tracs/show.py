
from datetime import datetime

from click import echo
from dateutil.tz import tzlocal
from rich import box
from rich.pretty import Pretty as pp
from rich.table import Table

from .activity import Activity
from .config import ApplicationContext
from .config import console
from .dataclasses import as_dict
from .utils import fmt

def show_activity( activities: [Activity], ctx: ApplicationContext, frmt: str = None, display_raw: bool = False ) -> None:
	for a in activities:
		if frmt is not None:
			try:
				echo( frmt.format_map( a ) )
			except KeyError:
				echo( "KeyError: invalid format string, check if provided fields really exist" )

		else:
			table = Table( box=box.MINIMAL, show_header=True, show_footer=False )

			if display_raw:
				table.add_column( '[blue]field' )
				table.add_column( '[blue]value' )
				for field, value in as_dict( a, remove_persist=False, remove_null=False ).items():
					if field not in ['metadata', 'resources']:
						table.add_row( field, pp( value ) )

				if ctx:
					table.add_row( '[blue]resources', '' )
					for uid in a.uids:
						resources = ctx.db.find_resources( uid )
						for r in resources:
							table.add_row( '', '' )
							for field, value in as_dict( r, remove_persist=False, remove_null=False ).items():
								table.add_row( field, pp( value ) )

			else:
				table.add_column( '[blue]field' )
				table.add_column( '[blue]value' )
				rows = [
					[ 'ID', a.id ],
					[ 'Name', a.name ],
					[ 'Type', a.type ],
					[ 'Time (local)', a.localtime ],
					[ 'Time (UTC)', a.time ],
					[ 'Timezone\u00b9', datetime.now( tzlocal()).tzname() ],
					[ 'Location', a.location_country ],
					[ 'Duration (elapsed)', a.duration ],
					[ 'Duration (moving)', a.duration_moving ],
					[ 'Distance', a.distance ],
					[ 'Ascent', a.ascent ],
					[ 'Descent', a.descent ],
					[ 'Elevation (highest)', a.elevation_max ],
					[ 'Elevation (lowest)', a.elevation_min ],
					[ 'Speed (average)', a.speed ],
					[ 'Speed (max)', a.speed_max ],
					[ 'Heart Rate (average)', a.heartrate ],
					[ 'Heart Rate (max)', a.heartrate_max ],
					[ 'Heart Rate (min)', a.heartrate_min ],
					[ 'Calories', a.calories ],
					[ 'Raw ID', a.raw_id ],
					[ 'UID', a.uid ],
				]

				for row in rows:
					if row[1] is None or row[1] == '':
						continue
					else:
						if type( row[1] ) is str:
							table.add_row( row[0], row[1] )
						elif type( row[1] ) in [int, float]:
							table.add_row( row[0], pp( row[1] ) )
						else:
							table.add_row( row[0], fmt( row[1] ) )

			console.print( table )
			console.print( '\u00b9 Proper timezone support is currently missing, local timezone is displayed' )

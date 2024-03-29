
from logging import getLogger
from typing import Any
from typing import List
from typing import Tuple

from rich.columns import Columns
from rich.prompt import IntPrompt

from .activity import Activity
from .activity_types import ActivityTypes
from .config import ApplicationContext
from .aio import load_all_resources
from .aio import open_activities
from .ui import Choice
from .utils import fmt

MSG_OPEN_APPLICATION = '<open/view GPX/TCX in default application>'

log = getLogger( __name__ )

def edit_activities( activities: [Activity] ):
	raise NotImplementedError( 'not yet implemented' )

def modify_activities( activities: List[Activity], field: str, value: Any, **kwargs ):
	ctx = kwargs.get( 'ctx', None )
	force = kwargs.get( 'force', False )
	pretend = kwargs.get( 'pretend', False )

	if ( f := Activity.field( field ) ) and ( not f.metadata.get( PROTECTED, False ) ):
		for a in activities:
			setattr( a, field, value )
			ctx.db.update( a )
	else:
		log.error( f'unable to set {field} to {value}: field does not exist or is protected' )

def rename_activities( activities: List[Activity], ctx: ApplicationContext, force: bool = False, pretend: bool = False ) -> None:
	for a in activities:
		ctx.console.print( f'renaming activity [{a.id}]' )
		ctx.console.print( f'  name                   : {a.name}' )
		ctx.console.print( f'  local time             : {fmt( a.starttime_local )}' )
		ctx.console.print( f'  place, city (country)  : {a.location_place}, {a.location_city} ({a.location_country})' )

		# resources = load_all_resources( ctx.db, a )

		headline = 'select a choice from the list below, press enter to use the default value or enter a new name directly:'
		choices = [ a.name, MSG_OPEN_APPLICATION ]
		choices_display = [ str( index + 1 ) for index in range( len( choices ) ) ]

		while True:
			answer = Choice.ask( default=a.name, headline=headline, choices=choices, choices_display=choices_display, allow_free_text=True )
			if answer == a.name or answer is None:
				break
			elif answer == MSG_OPEN_APPLICATION:
				open_activities( ctx, [a] )
			else:
				a.name = answer
				log.debug( f'renamed activity {a.id} to {answer}' )
				break

def set_activity_type( ctx: ApplicationContext, activities: List[Activity], activity_type: str ) -> None:
	if activity_type:
		if not ( activity_type := ActivityTypes.get( activity_type ) ):
			ctx.console.print( 'error: invalid type, use the [bold]types[/bold] command to find valid types' )
	else:
		types = sorted( ActivityTypes.names() )
		choices = [ str( i ) for i in range( 1, len( types ) + 1 ) ]
		display_values = [ f'[blue]\[{c}][/blue] {t}' for t, c in zip( types, choices ) ]

		ctx.console.print( Columns( display_values, padding=(0, 4), equal=True, column_first=True ) )
		index = IntPrompt.ask( 'Enter number of activity', console=ctx.console, choices=choices, show_choices=False ) - 1
		activity_type = ActivityTypes.get( types[index] )

	for a in activities:
		a.type = activity_type
	ctx.db.commit()

def tag_activities( activities: List[Activity], tags: List[str], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ) -> None:
	for a in activities:
		a.tags = sorted( list( set( a.tags ).union( set( tags ) ) ) )

def untag_activities( activities: List[Activity], tags: List[str], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ) -> None:
	for a in activities:
		a.tags = [t for t in a.tags if t not in tags]

def equip_activities( activities: List[Activity], equipments: List[str], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ) -> None:
	for a in activities:
		a.equipment = sorted( list( set( a.tags ).union( set( equipments ) ) ) )

def unequip_activities( activities: List[Activity], equipments: List[str], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ) -> None:
	for a in activities:
		a.equipment = [e for e in a.equipment if e not in equipments]

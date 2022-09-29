
from dataclasses import fields
from logging import getLogger
from typing import Any
from typing import List

from rich.prompt import Prompt

from .activity import Activity
from .config import GlobalConfig as gc
from .dataclasses import PROTECTED

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

def rename_activities( activities: [Activity], force: bool = False, pretend: bool = False ) -> None:
	for a in activities:
		answer = Prompt.ask( f'Enter new name for activity {a.id}', default=a['name'] )
		if answer != a.name:
			a['name'] = answer
			gc.db.update( a )
			log.debug( f'renamed activity {a.id} to {answer}' )

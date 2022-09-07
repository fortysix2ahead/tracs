
from logging import getLogger
from rich.prompt import Prompt

from .activity import Activity
from .config import GlobalConfig as gc

log = getLogger( __name__ )

def edit_activities( activities: [Activity] ):
	raise NotImplementedError( 'not yet implemented' )

def rename_activities( activities: [Activity], force: bool = False, pretend: bool = False ) -> None:
	for a in activities:
		answer = Prompt.ask( f'Enter new name for activity {a.id}', default=a['name'] )
		if answer != a.name:
			a['name'] = answer
			gc.db.update( a )
			log.debug( f'renamed activity {a.id} to {answer}' )

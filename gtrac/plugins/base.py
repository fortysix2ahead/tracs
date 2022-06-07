from logging import getLogger
from typing import Dict
from typing import Optional

from . import accessor
from . import accessors
from . import transformers
from . import writers
from ..activity_types import ActivityTypes
from ..config import KEY_CLASSIFER
from ..config import KEY_GROUPS
from ..utils import fromisoformat

log = getLogger( __name__ )

# general purpose accessors/transformers

@accessors( classifier=None )
def accessors():
	return {
#		'_classifier': lambda doc, doc_id: _classifier( doc, doc_id ),
		'id': lambda doc, doc_id: int( doc_id ),
		'raw_id': lambda doc, doc_id: int( doc_id ),
		'uid': lambda doc, doc_id: _uid( doc, doc_id ),
	}

@transformers( classifier=None )
def transformers():
	return {
		'time': lambda value: fromisoformat( value ),
		'localtime': lambda value: fromisoformat( value ),
		'type': lambda value: value if type( value ) is ActivityTypes else ActivityTypes.get( value ),
	}

@writers( classifier=None )
def writers():
	return {}

#class ActivityDocument( Document ):
#	pass

#@document( namespace='bikecitizens' )
#class BikecitizensDocument( ActivityDocument ):
#	pass

#@document
#class PolarDocument( ActivityDocument ):
#	pass

# helpers

def _uid( doc: Dict, doc_id: int ) -> Optional[str]:
	if len( doc.get( KEY_GROUPS, {} ).get( 'ids', [] ) ) > 0:
		return f'group:{doc_id}'
	else:
		return None

@accessor( classifier=None )
def _classifier( doc: Dict, doc_id: int ) -> Optional[str]:
	"""
	Helper for classifying group activities. todo: this should be moved somewhere else

	:param doc: document
	:param doc_id: document id
	:return: string with a list of services, separated by a comma
	"""
	if len( doc.get( KEY_GROUPS, {} ).get( 'ids', [] ) ) > 0:
		uids = doc.get( KEY_GROUPS ).get( 'uids', [] )
		return ','.join( sorted( list( set( [s.split( ':' )[0] for s in uids] ) ) ) )
	else:
		return None

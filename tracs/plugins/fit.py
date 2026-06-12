
from logging import getLogger
from typing import Any

from tracs.activity import Activity
from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, resource_type
from tracs.resources import ResourceType

log = getLogger( __name__ )

FIT_TYPE = 'application/fit'

class FITActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		pass

@resource_type
def fit_resource_types() -> ResourceType:
	return ResourceType( name=FIT_TYPE, recording=True )

@importer( type=FIT_TYPE )
class FITImporter( ResourceHandler ):

	TYPE: str = FIT_TYPE
	ACTIVITY_CLS = FITActivity

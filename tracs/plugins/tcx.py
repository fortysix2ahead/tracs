
from logging import getLogger
from typing import Any

from tracs.activity import Activity
from tracs.plugins import document
from tracs.plugins import importer
from tracs.plugins.handlers import ResourceHandler

log = getLogger( __name__ )

TCX_TYPE = 'application/xml+tcx'

@document( type=TCX_TYPE )
class TCXActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		pass

@importer( type=TCX_TYPE )
class TCXImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( type=TCX_TYPE, activity_cls=TCXActivity )


from logging import getLogger
from typing import Any

from tracs.activity import Activity
from tracs.plugins import document
from tracs.plugins import importer
from tracs.plugins.handlers import ResourceHandler

log = getLogger( __name__ )

FIT_TYPE = 'application/fit'

@document( type=FIT_TYPE )
class FITActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		pass

@importer( type=FIT_TYPE )
class FITImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( type=FIT_TYPE, activity_cls=FITActivity )

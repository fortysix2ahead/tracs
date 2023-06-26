
from logging import getLogger

from tracs.handlers import ResourceHandler
from tracs.registry import importer

log = getLogger( __name__ )

JPEG_TYPE = 'image/jpeg'

@importer( type=JPEG_TYPE )
class JpegImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=JPEG_TYPE )


from logging import getLogger

from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, resourcetype
from tracs.resources import ResourceType

log = getLogger( __name__ )

JPEG_TYPE = 'image/jpeg'

@resourcetype
def jpeg_resource_type() -> ResourceType:
	return ResourceType( type=JPEG_TYPE, image=True )

@importer( type=JPEG_TYPE )
class JpegImporter( ResourceHandler ):

	TYPE: str = JPEG_TYPE

	def __init__( self ) -> None:
		super().__init__( resource_type=JPEG_TYPE )

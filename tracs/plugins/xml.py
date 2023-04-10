
from lxml.objectify import fromstring

from tracs.registry import importer
from tracs.handlers import ResourceHandler
from tracs.resources import Resource

XML_TYPE = 'application/xml'

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	def load_data( self, resource: Resource, **kwargs ) -> None:
		resource.raw = fromstring( resource.content )

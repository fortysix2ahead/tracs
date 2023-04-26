from typing import Any, Union

from lxml.objectify import fromstring

from tracs.registry import importer
from tracs.handlers import ResourceHandler

XML_TYPE = 'application/xml'

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	def load_data( self, content: Union[bytes,str], **kwargs ) -> Any:
		return fromstring( content )

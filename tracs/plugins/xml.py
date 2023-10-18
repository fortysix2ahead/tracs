from typing import Any, Union

from lxml.objectify import fromstring

from tracs.registry import importer
from tracs.handlers import ResourceHandler

XML_TYPE = 'application/xml'

# todo: replace with @importer / remove duplicate type/cls information from here
@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	TYPE: str = XML_TYPE

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return fromstring( content )

from typing import Any, Union

from lxml.objectify import fromstring, ObjectifiedElement

from tracs.registry import importer, Registry
from tracs.handlers import ResourceHandler
from tracs.resources import ResourceType

XML_TYPE = 'application/xml'

# register XML type
Registry.register_resource_type( ResourceType( type=XML_TYPE, activity_cls=ObjectifiedElement ) )

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	TYPE: str = XML_TYPE

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return fromstring( content )

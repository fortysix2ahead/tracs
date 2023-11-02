from typing import Any, Union

from lxml.objectify import fromstring, ObjectifiedElement

from tracs.registry import importer, Registry, resourcetype
from tracs.handlers import ResourceHandler
from tracs.resources import ResourceType

XML_TYPE = 'application/xml'

@resourcetype
def xml_resource_type() -> ResourceType:
	return ResourceType( type=XML_TYPE, activity_cls=ObjectifiedElement )

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	TYPE: str = XML_TYPE

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return fromstring( content )

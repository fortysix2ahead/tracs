
from typing import Any
from typing import Optional
from typing import Type

from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from tracs.registry import importer
from tracs.handlers import ResourceHandler
from tracs.resources import Resource

JSON_TYPE = 'application/json'

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load_data( self, resource: Resource, **kwargs ) -> None:
		resource.raw = load_json( resource.content )

	def save_data( self, data: Any, **kwargs ) -> bytes:
		return save_json( data, option=JSONHandler.options )

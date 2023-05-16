
from typing import Any, Union

from orjson import dumps as save_json, loads as load_json, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS

from tracs.handlers import ResourceHandler
from tracs.registry import importer

JSON_TYPE = 'application/json'

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return load_json( content )

	def save_raw( self, data: Any, **kwargs ) -> bytes:
		return save_json( data, option=JSONHandler.options )

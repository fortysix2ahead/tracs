from __future__ import annotations

from logging import getLogger
from typing import Any, Union

from dataclass_factory import Factory
from orjson import dumps as save_json, loads as load_json, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS

from tracs.handlers import log, ResourceHandler
from tracs.registry import importer

log = getLogger( __name__ )

JSON_TYPE = 'application/json'

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return load_json( content )

	def save_raw( self, data: Any, **kwargs ) -> bytes:
		return save_json( data, option=JSONHandler.options )

class DataclassFactoryHandler( JSONHandler ):

	def __init__( self ):
		super().__init__()
		self._factory: Factory = Factory( debug_path=True, schemas={} ) # use dataclass factory instead of callable

	def load_data( self, raw: Any, **kwargs ) -> Any:
		"""
		Transforms raw data into structured data. If raw data is a dict and an activity class is set, it will use
		the dataclass factory to try a transformation. Will return raw data in case that fails.
		Example: transform a dict into a dataclass.
		"""
		try:
			return self._factory.load( raw, self._activity_cls )
		except RuntimeError:
			log.error( f'unable to transform raw data into structured data by using the factory for {self._activity_cls}', exc_info=True )
			return raw

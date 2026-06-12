from __future__ import annotations

from datetime import timedelta
from logging import getLogger
from typing import Any, Union

from orjson import dumps as save_json, loads as load_json

from tracs.constants import ORJSON_OPTIONS
from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, resource_type
from tracs.resources import ResourceType
from tracs.utils import timedelta_to_str

log = getLogger( __name__ )

JSON_TYPE = 'application/json'

@resource_type
def json_resource_type() -> ResourceType:
	return ResourceType( name=JSON_TYPE )

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	TYPE: str = JSON_TYPE

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return load_json( content )

	def save_raw( self, data: Any, **kwargs ) -> bytes:
		return save_json( data, option=ORJSON_OPTIONS, default=serialize )

class DataclassFactoryHandler( JSONHandler ):

	def load_data( self, raw: Any, **kwargs ) -> Any:
		"""
		Transforms raw data into structured data. If raw data is a dict and an activity class is set, it will use
		the dataclass factory to try a transformation. Will return raw data in case that fails.
		Example: transform a dict into a dataclass.
		"""
		try:
			return kwargs.get( 'converter' ).structure( raw, kwargs.get( 'cls' ) )
		except RuntimeError:
			log.error( f'unable to transform raw data into structured data by using the converter/cls {kwargs.get( "converter" )}, {kwargs.get( "cls" )}', exc_info=True )
			return raw

def serialize( obj: Any ):
	if isinstance( obj, timedelta ):
		return timedelta_to_str( obj )
	raise TypeError

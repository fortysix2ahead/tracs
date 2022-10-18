
from csv import field_size_limit
from csv import reader as csv_reader
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Type
from typing import Union

from lxml.etree import parse as parse_xml
from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from . import importer
from ..activity import Activity
from ..activity import Resource

CSV_TYPE = 'application/csv'
JSON_TYPE = 'application/json'
XML_TYPE = 'application/xml'
TCX_TYPE = 'application/xml+tcx'

class ResourceHandler:

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		self._activity_cls: Optional[Type] = activity_cls
		self._type: Optional[str] = type

	def load( self, data: Optional[Any] = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Union[Activity, Resource]]:
		as_resource = kwargs.get( 'as_resource', False ) # flag to force to return a resource even when an activity class is available
		as_string = kwargs.get( 'as_string', False ) # flag to signal to read binary data only
		as_binary = kwargs.get( 'as_binary', False ) # flag to signal to return only a string
		encoding = kwargs.get( 'encoding', 'UTF-8' ) # encoding to use when converting from bytes to str

		# try to load from url if provided
		_content = self.load_url( url, **kwargs ) if url else None

		# try to load from path if provided, but don't overwrite loaded data
		_content = self.load_path( path, **kwargs ) if path and not _content else None

		# decode the content into a string
		_text = self.load_text( _content, **kwargs ) if _content else None

		# try load/process either provided or loaded data
		_data = self.load_data( _text or _content ) if not data else data

		# postprocess data
		_data = self.postprocess_data( _data, _text, _content, path, url )

		# transform into activity, if activity class is set otherwise return as structured data
		resource = self.create_resource( _data, _text, _content, path, url )

		# create an activity
		activity = self.create_activity( resource ) if not as_resource else None

		return activity or resource


	def load_url( self, url: str, **kwargs ) -> Optional[bytes]:
		pass

	def load_path( self, path: Path, **kwargs ) -> Optional[bytes]:
		return path.read_bytes()

	# noinspection PyMethodMayBeStatic
	def load_text( self, content: bytes, **kwargs ) -> Optional[str]:
		return content.decode( 'UTF-8' )

	def load_data( self, text: Any, **kwargs ) -> Any:
		return text

	def postprocess_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		return data

	def create_resource( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Resource:
		return Resource(
			type=self.type,
			path=path.name if path else None,
			source=path.as_uri() if path else None,
			status=200,
			raw=data,
			text=text,
			content=content
		)

	def create_activity( self, resource: Resource ) -> Optional[Activity]:
		return self.activity_cls( raw=resource.raw, resources=[ resource ] ) if self.activity_cls else None

	@property
	def type( self ) -> Optional[str]:
		return self._type

	@property
	def activity_cls( self ) -> Optional[Type]:
		return self._activity_cls

	# noinspection PyMethodMayBeStatic
	def save_content( self, content: bytes, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> None:
		if path:
			path.write_bytes( content )

	# noinspection PyMethodMayBeStatic
	def save_text( self, text: str, **kwargs ) -> bytes:
		return text.encode( encoding = 'UTF-8' )

	def save_data( self, data: Any, **kwargs ) -> str:
		pass

	def save( self, data: Any = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> None:
		_text = self.save_data( data )
		_content = self.save_text( _text )
		self.save_content( _content, path, url, **kwargs )

@importer( type=CSV_TYPE )
class CSVHandler( ResourceHandler ):

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None, **kwargs ) -> None:
		super().__init__( type=type or JSON_TYPE, activity_cls=activity_cls )

		self._field_size_limit = kwargs.get( 'field_size_limit', 131072 ) # keep this later use
		field_size_limit( self._field_size_limit )

	def load_data( self, text: str, **kwargs ) -> Any:
		return [ r for r in csv_reader( text.splitlines() ) ]

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		super().__init__( type=type or JSON_TYPE, activity_cls=activity_cls )

	def load_data( self, text: str, **kwargs ) -> Any:
		return load_json( text )

	def save_data( self, data: Any, **kwargs ) -> str:
		return save_json( data, option=JSONHandler.options ).decode( 'UTF-8' )

	def save( self, data: Any = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> None:
		self.save_content( content=save_json( data, option=JSONHandler.options ), path=path, url=url, **kwargs )

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		super().__init__( type=type or XML_TYPE, activity_cls=activity_cls )

	def postprocess_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		return parse_xml( path )


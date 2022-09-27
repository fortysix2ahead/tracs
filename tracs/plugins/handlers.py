
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

from dateutil.tz import UTC
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX
from lxml.etree import parse as parse_xml
from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from . import document
from . import importer
from ..activity import Activity
from ..activity import Resource
from ..utils import seconds_to_time

JSON_TYPE = 'application/json'
XML_TYPE = 'application/xml'
GPX_TYPE = 'application/xml+gpx'
TCX_TYPE = 'application/xml+tcx'

class ResourceHandler:

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		self._activity_cls: Optional[Type] = activity_cls
		self._type: Optional[str] = type

	def load( self, data: Optional[Any] = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Union[Activity, Resource]]:
		# try to load from url if provided
		_content = self.load_url( url, **kwargs ) if url else None

		# try to load from path if provided, but don't overwrite loaded data
		_content = self.load_path( path, **kwargs ) if path and not _content else None

		# decode the content into a string
		_text = self.load_text( _content, **kwargs ) if _content else None

		# try load/process either provided or loaded data
		_data = self.load_data( data or _text or _content )

		# postprocess data
		_data = self.postprocess_data( _data, _text, _content, path, url )

		# transform into activity, if activity class is set otherwise return as structured data
		resource = self.create_resource( _data, _text, _content, path, url )

		# create an activity
		activity = self.create_activity( resource )

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
		return Resource( type=self.type, path=path.name, source=path.as_uri(), status=200, raw=data, text=text, content=content )

	def create_activity( self, resource: Resource ) -> Optional[Activity]:
		return self.activity_cls( raw=resource.raw, resources=[ resource ] ) if self.activity_cls else None

	@property
	def type( self ) -> Optional[str]:
		return self._type

	@property
	def activity_cls( self ) -> Optional[Type]:
		return self._activity_cls

	def save( self, data: Union[Dict, str, bytes], path: Optional[Path] = None, url: Optional[str] = None ) -> None:
		with open( file=path, mode='w+', buffering=8192, encoding='UTF-8' ) as p:
			if isinstance( data, dict ):
				p.write( self.save_dict( data ) )

	# noinspection PyMethodMayBeStatic
	def save_dict( self, data: Dict ) -> Union[str, bytes]:
		return str( data )

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		super().__init__( type=type or JSON_TYPE, activity_cls=activity_cls )

	def load_data( self, text: str, **kwargs ) -> Any:
		return load_json( text )

	def save_dict( self, data: Dict ) -> Union[str, bytes]:
		return save_json( data, option=JSONHandler.options ).decode( 'UTF-8' )

@importer( type=XML_TYPE )
class XMLHandler( ResourceHandler ):

	def __init__( self, type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		super().__init__( type=type or XML_TYPE, activity_cls=activity_cls )

	def postprocess_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		return parse_xml( path )

@document( type=GPX_TYPE )
class GPXActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		gpx: GPX = self.raw
		self.name = gpx.name
		self.time = gpx.get_time_bounds().start_time.astimezone( UTC )
		self.distance = round( gpx.length_2d(), 1 )
		self.duration = seconds_to_time( gpx.get_duration() ) if gpx.get_duration() else None
		self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )
		# self.uid = f'{self.classifier}:{self.raw_id}'

@importer( type=GPX_TYPE )
class GPXImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( type=XML_TYPE, activity_cls=GPXActivity )

	def postprocess_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		return parse_gpx( content )

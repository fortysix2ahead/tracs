
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from dateutil.tz import UTC
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX
from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from . import importer
from ..activity import Activity
from ..activity import Resource
from ..utils import seconds_to_time

JSON_TYPE = 'application/json'
GPX_TYPE = 'application/xml+gpx'
TCX_TYPE = 'application/xml+tcx'

class ResourceHandler:

	def __init__( self ) -> None:
		self._types: List[str] = []

	def load( self, data: Optional[Any] = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Any]:
		# try to load from url if provided
		_loaded_data = self.load_url( url, **kwargs ) if url else None

		# try to load from path if provided, but don't overwrite loaded data
		_loaded_data = self.load_path( path, **kwargs ) if path and not _loaded_data else None

		# try load/process either provided or loaded data
		_structured_data = self.load_data( data or _loaded_data )

		# transform into activity, if activity class is set
		# noinspection PyArgumentList
		#_data = self.activity_cls( raw = _structured_data ) if self.activity_cls and _structured_data else _structured_data
		_data = self.postprocess_data( _structured_data, _loaded_data, path, url )

		return _data

	def load_data( self, data: Any, **kwargs ) -> Any:
		pass

	# noinspection PyMethodMayBeStatic
	def load_path( self, path: Path, **kwargs ) -> Optional[Union[str, bytes]]:
		with open( path, encoding='utf-8', mode='r', buffering=8192 ) as p:
			return p.read()

	def load_url( self, url: str, **kwargs ) -> Any:
		pass

	# noinspection PyMethodMayBeStatic
	def postprocess_data( self, structured_data: Any, loaded_data: Any, path: Optional[Path], url: Optional[str] ) -> Any:
		return structured_data

	def save( self, data: Union[Dict, str, bytes], path: Optional[Path] = None, url: Optional[str] = None ) -> None:
		with open( file=path, mode='w+', buffering=8192, encoding='UTF-8' ) as p:
			if isinstance( data, dict ):
				p.write( self.save_dict( data ) )

	# noinspection PyMethodMayBeStatic
	def save_dict( self, data: Dict ) -> Union[str, bytes]:
		return str( data )

	@property
	def types( self ) -> List[str]:
		return self._types

@importer( type=JSON_TYPE )
class JSONHandler( ResourceHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load_data( self, data: Any, **kwargs ) -> Activity:
		return load_json( data )

	def save_dict( self, data: Dict ) -> Union[str, bytes]:
		return save_json( data, option=JSONHandler.options ).decode( 'UTF-8' )

@dataclass
class GPXActivity( Activity ):

	def __post_init__( self ):
		super().__post_init__()

		if self.raw:
			gpx: GPX = self.raw
			self.name = gpx.name
			self.time = gpx.get_time_bounds().start_time.astimezone( UTC )
			self.distance = round( gpx.length_2d(), 1 )
			self.duration = seconds_to_time( gpx.get_duration() ) if gpx.get_duration() else None
			self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )

@importer( type=GPX_TYPE )
class GPXImporter( ResourceHandler ):

	def load_data( self, data: Any, **kwargs ) -> Any:
		return parse_gpx( data )

	def postprocess_data( self, structured_data: Any, loaded_data: Any, path: Optional[Path], url: Optional[str] ) -> Any:
		resource = Resource( type=GPX_TYPE, path=path.name, source=path.as_uri(), status=200, raw=structured_data, raw_data=loaded_data )
		activity = GPXActivity( raw=structured_data, resources=[resource] )
		return activity

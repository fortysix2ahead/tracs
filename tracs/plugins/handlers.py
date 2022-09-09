
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

from . import handler
from . import importer
from ..activity import Activity
from ..activity import Resource
from ..base import Handler
from ..base import Importer
from ..utils import seconds_to_time

@handler( types=['json'] )
class JSONHandler( Handler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load( self, path: Optional[Path] = None, data: Optional[Union[str, bytes]] = None ) -> Union[Dict, Any]:
		data = self.load_raw( path ) if path else data
		return load_json( data ) if data else None

	def save( self, path: Path, data: Union[Dict, str, bytes] ) -> None:
		with open( file=path, mode='w+', buffering=8192, encoding='UTF-8' ) as p:
			p.write( save_json( data, option=JSONHandler.options ).decode( 'UTF-8' ) )

	def types( self ) -> List[str]:
		return [ 'json' ]

@dataclass
class GPXActivity( Activity ):

	def __post_init__( self ):
		super().__post_init__()

		if self.raw:
			gpx: GPX = self.raw
			self.name = gpx.name
			self.time = gpx.get_time_bounds().start_time.astimezone( UTC )
			self.duration = seconds_to_time( gpx.get_duration() ) if gpx.get_duration() else None
			self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )

@handler( types=['gpx'] )
@importer( types=['gpx'] )
class GPXHandler( Handler, Importer ):

	def load( self, path: Optional[Path] = None, data: Optional[Union[str, bytes]] = None ) -> Union[Dict, Any]:
		data = self.load_raw( path ) if path else data
		return parse_gpx( data ) if data else None

	def save( self, path: Path, content: Union[Dict, Activity] ) -> None:
		raise RuntimeError( 'not supported yet' )

	def types( self ) -> List[str]:
		return [ 'gpx' ]

	def import_from( self, data: Any = None, path: Optional[Path] = None, **kwargs ) -> Activity:
		activity = None
		raw_data = kwargs.get( 'raw_data' )

		if path:
			raw_data = self.load_raw( path ) if not raw_data else raw_data
			resources = [Resource( path=path.name, type=self.types()[0], raw_data=raw_data, source=path.as_uri(), status=100 )]
			if not data:
				data = self.load( data = raw_data )
		else:
			resources = []

		if data:
			activity = GPXActivity( raw=data, resources=resources )

		return activity


from pathlib import Path
from typing import Dict
from typing import Protocol
from typing import Union

from attr import define
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX
from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from . import handler
from ..activity import Activity

class DocumentHandler( Protocol ):

	def load( self, path: Path ) -> Union[Dict]:
		pass

	def save( self, path: Path, content: Union[Dict] ) -> None:
		pass

@handler( type='json' )
class JSONHandler( DocumentHandler ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def load( self, path: Path ) -> Union[Dict]:
		with open( file=path, mode='r', buffering=8192, encoding='UTF-8' ) as p:
			return load_json( p.read() )

	def save( self, path: Path, content: Union[Dict] ) -> None:
		with open( file=path, mode='w+', buffering=8192, encoding='UTF-8' ) as p:
			p.write( save_json( content, option=JSONHandler.options ).decode( 'UTF-8' ) )

@define
class GPXActivity( Activity ):

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.raw:
			gpx: GPX = self.raw
			self.name = gpx.name
			self.time = gpx.time

@handler( type='gpx' )
class GPXHandler( DocumentHandler ):

	def load( self, path: Path ) -> Union[Dict, Activity]:
		with open( path, encoding='utf-8', mode='r', buffering=8192 ) as p:
			return GPXActivity( raw=parse_gpx( p ) )

	def save( self, path: Path, content: Union[Dict, Activity] ) -> None:
		raise RuntimeError( 'not supported yet' )

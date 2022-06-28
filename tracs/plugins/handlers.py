
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Protocol
from typing import Union

from orjson import loads as load_json
from orjson import dumps as save_json
from orjson import OPT_APPEND_NEWLINE
from orjson import OPT_INDENT_2
from orjson import OPT_SORT_KEYS

from . import handler

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
		with open( file=path, mode='b+', buffering=8192, encoding='UTF-8' ) as p:
			p.write( save_json( content, option=JSONHandler.options ) )

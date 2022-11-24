
from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from fs.errors import ResourceNotFound
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from orjson import dumps as dump_as_json
from orjson import JSONDecodeError
from orjson import loads as load_json
from orjson import OPT_PASSTHROUGH_DATACLASS
from orjson.orjson import OPT_APPEND_NEWLINE
from orjson.orjson import OPT_INDENT_2
from orjson.orjson import OPT_SORT_KEYS
from tinydb.storages import Storage

from tracs.activity import Activity
from tracs.resources import Resource

log = getLogger( __name__ )

EMPTY_JSON = '{}'

class DataClassStorage( Storage ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS
	options_passthrough = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS | OPT_PASSTHROUGH_DATACLASS
	memory_path = '/storage.json'

	def __init__( self, path: Optional[Path], encoding: str = 'UTF-8', read_only: bool = False, passthrough: bool = True ):
		super().__init__()
		self.path = path
		self.encoding = encoding
		self.read_only = read_only
		self.passthrough = passthrough
		self.options = DataClassStorage.options_passthrough if passthrough else DataClassStorage.options

		self.fs = MultiFS()
		self.fs.add_fs( 'underlay', OSFS( root_path='/' ), write=False )
		self.fs.add_fs( 'overlay', MemoryFS(), write=True )
		self.ofs, self.ufs = self.fs.get_fs( 'overlay' ), self.fs.get_fs( 'underlay' )

		try:
			self.ofs.writebytes( DataClassStorage.memory_path, self.ufs.readbytes( str( self.path ) ) )
		except ResourceNotFound:
			self.ofs.writebytes( DataClassStorage.memory_path, b'' )

	# helper methods for testing

	def mem_as_bytes( self ) -> bytes:
		return self.ofs.readbytes( DataClassStorage.memory_path )

	def mem_as_str( self ) -> str:
		return self.ofs.readtext( DataClassStorage.memory_path, encoding='UTF-8' )

	def mem_as_dict( self ) -> Dict:
		try:
			return load_json( self.mem_as_bytes() )
		except JSONDecodeError:
			return {}

	# read/write/close

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		return self.mem_as_dict()

	def write( self, data: Dict[str, Dict[str, Any]] ) -> None:
		self.ofs.writebytes( DataClassStorage.memory_path, dump_as_json( data, default=default, option=self.options ) )

	def close( self ) -> None:
		if not self.read_only:
			self.ufs.writebytes( str( self.path ), self.ofs.readbytes( DataClassStorage.memory_path ) )

	# custom serialization

	def serialize( self ) -> None:
		pass

# default customization

def default( obj ):
	if isinstance( obj, (Activity, Resource) ):
		return obj.asdict()
	raise TypeError

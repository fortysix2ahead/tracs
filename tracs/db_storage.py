
from __future__ import annotations

from datetime import datetime
from datetime import time
from io import UnsupportedOperation
from inspect import isfunction
from logging import getLogger
from os import fsync
from os import SEEK_END
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type

from fs.errors import ResourceNotFound
from fs.memoryfs import MemoryFS
from fs.multifs import MultiFS
from fs.osfs import OSFS
from orjson import JSONDecodeError
from orjson import loads as load_json
from orjson import dumps as dump_as_json
from orjson import OPT_PASSTHROUGH_DATACLASS
from orjson.orjson import OPT_APPEND_NEWLINE
from orjson.orjson import OPT_INDENT_2
from orjson.orjson import OPT_SORT_KEYS
from tinydb.storages import MemoryStorage
from tinydb.storages import Storage

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.dataclasses import as_dict
from tracs.resources import Resource

log = getLogger( __name__ )

EMPTY_JSON = '{}'

# based on tinydb.JSONStorage, adjusted to use OrJSON

class OrJSONStorage( Storage ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def __init__( self, path: Path, create_dirs: bool = False, encoding: str = 'UTF-8', access_mode: str = 'r+', serializers: Dict[str, Callable] = None, deserializers: Dict[str, Callable] = None ):
		super().__init__()

		self.path = path
		self.encoding = encoding
		self.access_mode = access_mode
		self.serializers = serializers # reserved for future use
		self.deserializers = deserializers

		# Create the file if it doesn't exist and creating is allowed by the access mode
		if any( [character in self.access_mode for character in ('+', 'w', 'a')] ):  # any of the writing modes
			self.path.touch( exist_ok=True )

		# Open the file for reading/writing
		self.handle = open( self.path, mode=self.access_mode, encoding=encoding )

	def close( self ) -> None:
		self.handle.close()

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		# Get the file size by moving the cursor to the file end and reading its location
		self.handle.seek( 0, SEEK_END )
		size = self.handle.tell()

		if not size:
			data = None # File is empty, so we return ``None`` so TinyDB can properly initialize the database
		else:
			self.handle.seek( 0 ) # Return the cursor to the beginning of the file
			data = load_json( self.handle.read() ) # Load the JSON contents of the file

		if self.deserializers:
			for table_name, table in data.items():
				for doc_id, doc in table.items():
					for key, value in doc.items():
						if key in self.deserializers.keys():
							doc[key] = self.deserializers[key]( doc[key] )

		return data

	def write( self, data: Dict[str, Dict[str, Any]] ):
		self.handle.seek( 0 ) # Move the cursor to the beginning of the file just in case
		serialized = dump_as_json( data, option=self.options ) # Serialize the database state using options from above

		# Write the serialized data to the file
		try:
			self.handle.write( serialized.decode( self.encoding ) )
		except UnsupportedOperation:
			raise IOError( f'Unable to write database to {self.path}, access mode is {self.access_mode}' )

		# Ensure the file has been written
		self.handle.flush()
		fsync( self.handle.fileno() )
		self.handle.truncate() # Remove data that is behind the new cursor in case the file has gotten shorter

class DataClassStorage( Storage ):
	"""
	Unifies middleware/storage requirements without fiddling around with tinydb middleware/storage instantiation chain.
	"""

	# serializers/deserializers
	serializers: Dict[str, Callable] = {
		'time': lambda v: v.isoformat()
	}

	deserializers: Dict[str,Callable] = {
		'duration': lambda v: time.fromisoformat( v ),
		'duration_moving': lambda v: time.fromisoformat( v ),
		'localtime': lambda v: datetime.fromisoformat( v ),
		'localtime_end': lambda v: datetime.fromisoformat( v ),
		'time': lambda v: datetime.fromisoformat( v ),
		'time_end': lambda v: datetime.fromisoformat( v ),
		'type': lambda v: ActivityTypes.get( v )
	}

	def __init__( self,
	              path: Path = None,
	              use_memory_storage: bool = False,
	              access_mode: str = 'r+',
	              use_cache: bool = False,
	              cache_size: int = 1000,
	              passthrough: bool = True,
	              use_serializers: bool = True ):
		super().__init__()

		self.use_memory_storage = use_memory_storage if path else True  # auto-turn on memory mode when no path is provided
		self.memory_storage = MemoryStorage()

		self.serializers = DataClassStorage.serializers if use_serializers else None
		self.deserializers = DataClassStorage.deserializers if use_serializers else None

		self.json_storage = OrJSONStorage( path, access_mode=access_mode, serializers=self.serializers, deserializers=self.deserializers ) if path else None
		self.data = self.json_storage.read() if self.json_storage else None
		self.memory_storage.write( self.data )

		self.use_cache = use_cache if not self.use_memory_storage else True  # turn on cache if in-memory mode is on
		self.cache_hits = 0
		self.cache_size = cache_size if self.use_cache else 0

		self.remove_null_fields: bool = True  # don't write fields which do not have a value
		self.passthrough = passthrough
		self.document_cls: Type = Activity

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		data = self.memory_storage.read() if self.use_cache else self.json_storage.read() # read data from cache or file
		data = data if self.passthrough else self.transform_data( data )  # transform data
		return data # return read data

	def transform_data( self, data ) -> Any:
		if data:
			for table_name, table_data in data.items():
				self.transform_table( table_data )
		return data

	def transform_table( self, table_data: Dict ) -> None:
		for item_id, item_data in table_data.items():
			table_data[item_id] = self.transform_item( item_id, item_data )

	def transform_item( self, item_id: str, item_data: Any ) -> Optional:
		return self.document_cls( data=item_data, doc_id=int( item_id ) )

	def write( self, data: Dict[str, Dict[str, Any]] ) -> None:
		# process data
		data = data if self.passthrough else self.write_data( data )
		self.memory_storage.write( data ) # save data to memory and increase cache counter

		# persist data if not in memory mode and cache hits size
		if not self.use_memory_storage and self.cache_hits >= self.cache_size:
			self.json_storage.write( data )
			self.cache_hits = 0

		# increase cache hits
		self.cache_hits += 1

	def write_data( self, data: Dict[str, Dict[str, Any]] ) -> Any:
		if data:
			for table_name, table_data in data.items():
				self.write_table( table_name, table_data )
		return data

	def write_table( self, table_name: str, table_data: Dict ):
		for item_id, item_data in dict( table_data ).items():
			if replacement := self.write_item( item_id, item_data ):
				table_data[item_id] = replacement

	# noinspection PyMethodMayBeStatic
	def write_item( self, item_id: str, item: Any ) -> Optional:
		item_cls = self._document_factory( item, item_id ) if isfunction( self._document_factory ) else self._document_factory
		# todo: item_cls might be None and Document needs to be used
		return as_dict( item, item_cls, modify_arg=True, remove_null=self._remove_null_fields )

	def flush( self ) -> None:
		data = self.memory_storage.read()
		if self.json_storage:
			self.json_storage.write( data )

	def close( self ) -> None:
		self.flush()

class DataClassStorage2( Storage ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS
	options_passthrough = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS | OPT_PASSTHROUGH_DATACLASS
	memory_path = '/storage.json'

	def __init__( self, path: Optional[Path], encoding: str = 'UTF-8', read_only: bool = False, passthrough: bool = True ):
		super().__init__()
		self.path = path
		self.encoding = encoding
		self.read_only = read_only
		self.passthrough = passthrough
		self.options = DataClassStorage2.options_passthrough if passthrough else DataClassStorage2.options

		self.fs = MultiFS()
		self.fs.add_fs( 'underlay', OSFS( root_path='/' ), write=False )
		self.fs.add_fs( 'overlay', MemoryFS(), write=True )
		self.ofs, self.ufs = self.fs.get_fs( 'overlay' ), self.fs.get_fs( 'underlay' )

		try:
			self.ofs.writebytes( DataClassStorage2.memory_path, self.ufs.readbytes( str( self.path ) ) )
		except ResourceNotFound:
			self.ofs.writebytes( DataClassStorage2.memory_path, b'' )

	# helper methods for testing

	def mem_as_bytes( self ) -> bytes:
		return self.ofs.readbytes( DataClassStorage2.memory_path )

	def mem_as_str( self ) -> str:
		return self.ofs.readtext( DataClassStorage2.memory_path, encoding='UTF-8' )

	def mem_as_dict( self ) -> Dict:
		try:
			return load_json( self.mem_as_bytes() )
		except JSONDecodeError:
			return {}

	# read/write/close

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		return self.mem_as_dict()

	def write( self, data: Dict[str, Dict[str, Any]] ) -> None:
		self.ofs.writebytes( DataClassStorage2.memory_path, dump_as_json( data, default=default, option=self.options ) )

	def close( self ) -> None:
		if not self.read_only:
			contents = self.fs.get_fs( 'overlay' ).readbytes( self.path.name )
			self.fs.get_fs( 'underlay' ).writebytes( str( self.path ), contents )

	# custom serialization

	def serialize( self ) -> None:
		pass

# default customization

def default( obj ):
	if isinstance( obj, (Activity, Resource) ):
		return obj.asdict()
	raise TypeError

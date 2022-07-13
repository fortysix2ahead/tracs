from __future__ import annotations

from datetime import datetime
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

from orjson import loads as load_json
from orjson import dumps as dump_as_json
from orjson.orjson import OPT_APPEND_NEWLINE
from orjson.orjson import OPT_INDENT_2
from orjson.orjson import OPT_SORT_KEYS
from tinydb.storages import MemoryStorage
from tinydb.storages import Storage

from tracs.dataclasses import as_dict

log = getLogger( __name__ )

EMPTY_JSON = '{}'

# based on tinydb.JSONStorage, adjusted to use OrJSON

class OrJSONStorage( Storage ):

	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def __init__( self, path: Path, create_dirs: bool = False, encoding: str = 'UTF-8', access_mode: str = 'r+', deserializers: Dict = None, **kwargs ):
		super().__init__()

		self.path = path
		self.encoding = encoding
		self.access_mode = access_mode
		self.deserializers = deserializers
		self.kwargs = kwargs

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

		#self._path.write_bytes( dump_as_json( data, option=self.orjson_options ) )
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

	# options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS| OPT_PASSTHROUGH_SUBCLASS
	orjson_options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	# map of converters field_name -> ( serializer_function, deserializer_function )
	converters: Dict[str, Tuple[Callable[[datetime], str], Callable[[str], datetime]]] = {
		'time': ( lambda v: v.isoformat(), lambda s: datetime.fromisoformat( s ) )
	}

	def __init__( self, path: Path = None, use_memory_storage: bool = False, access_mode: bool = 'r+', cache: bool = False, cache_size: int = 1000, passthrough=False, document_factory=None, *args, **kwargs ):
		super().__init__()

		self._initial_read = True
		self._memory_changed = False

		self._path = path
		self._access_mode = 'r' if use_memory_storage else access_mode
		self._buffering = 8192
		self._encoding = 'UTF-8'

		self._use_memory_storage = use_memory_storage if path else True  # auto-turn on memory mode when no path is provided
		self._memory = MemoryStorage()

		self._use_cache = cache if not self._use_memory_storage else True  # turn on cache if in-memory mode is on
		self._cache_hits = 0
		self._cache_size = cache_size if self._use_cache else 0

		self._document_factory = document_factory
		self._remove_null_fields: bool = True  # don't write fields which do not have a value
		self._passthrough = passthrough

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		# initial read, either because cache mode is off or it's the initial load
		if not self._use_cache or self._initial_read:
			data = self.read_data_from_path()
			self._initial_read = False
		else:
			data = self.memory.read()

		# transform data
		data = self.read_data( data ) if not self._passthrough else data

		# save data in memory
		self._memory.write( data )

		# return read data
		return data

	def read_data( self, data ) -> Any:
		if data:
			for table_name, table_data in data.items():
				self.read_table( table_data )
		return data

	def read_table( self, table_data: Dict ) -> None:
		for item_id, item_data in dict( table_data ).items():
			if replacement := self.read_item( item_id, item_data ):
				table_data[item_id] = replacement

	def read_item( self, item_id: str, item_data: Any ) -> Optional:
		if isfunction( self._document_factory ):
			item_cls = self._document_factory( item_data, item_id )
		else:
			item_cls = self._document_factory
		return item_cls( item_data, int( item_id ) ) if item_cls else None

	def read_data_from_path( self ) -> Any:
		if self._path:
			with open( self._path, self._access_mode, self._buffering, self._encoding ) as p:
				data = p.read()
				return load_json( data if len( data ) > 0 else EMPTY_JSON )
		return None

	def write( self, data: Dict[str, Dict[str, Any]] ) -> None:
		# process data
		data = self.write_data( data ) if not self._passthrough else data

		# save data to memory and increase cache counter
		self._memory.write( data )
		self._memory_changed = True

		# persist data if not in memory mode and cache hits size
		if not self._use_memory_storage and self._cache_hits >= self._cache_size:
			self.flush()
			self._cache_hits = 0

		# increase cache hits
		self._cache_hits += 1

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
		data = self._memory.read()
		if self._path and data:
			if self._memory_changed:
				data = self.write_data( data )  # do final conversion to dict as memory might contain unconverted data
				self._path.write_bytes( dump_as_json( data, option=self.orjson_options ) )
				self._memory_changed = False  # keep track of 'persist necessary' status
		else:
			log.debug( 'db storage flush called without path and/or data' )

	def close( self ) -> None:
		self.flush()

	@property
	def document_factory( self ) -> Callable:
		return self._document_factory

	@document_factory.setter
	def document_factory( self, fn: Callable ) -> None:
		self._document_factory = fn

	@property
	def memory( self ) -> MemoryStorage:
		return self._memory

#	@property
#	def transformation_map( self ):
#		return self._transformation_map

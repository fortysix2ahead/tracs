
from __future__ import annotations

from inspect import isfunction
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

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

class DataClassStorage( Storage ):
	"""
	Unifies middleware/storage requirements without fiddling around with tinydb middleware/storage instantiation chain.

	"""

	#options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS| OPT_PASSTHROUGH_SUBCLASS
	orjson_options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	def __init__( self, path: Path=None, use_memory_storage: bool=False, access_mode: bool = 'r+', cache: bool=False, cache_size: int=1000, passthrough=False, document_factory=None, *args, **kwargs ):
		super().__init__()

		self._initial_read = True
		self._initial_write = True # not used ...

		self._path = path
		self._access_mode = 'r' if use_memory_storage else access_mode
		self._buffering = 8192
		self._encoding = 'UTF-8'

		self._memory = MemoryStorage()
		self._use_memory_storage = use_memory_storage if path else True # auto-turn on memory mode when no path is provided

		self._use_cache = cache if not self._use_memory_storage else True # turn on cache if in-memory mode is on
		self._cache_hits = 0
		self._cache_size = cache_size if self._use_cache else 0

		self._document_factory = document_factory
		if not self._document_factory:
			log.debug( 'data storage initialized without a document factory' )
		#self._transformation_map: Dict[str, Union[Type, Callable]] = {}
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
		return as_dict( item, item_cls, modify_arg=True, remove_null_fields=self._remove_null_fields )

	def flush( self ) -> None:
		data = self._memory.read()
		if self._path and data:
			self._path.write_bytes( dump_as_json( data, option=self.orjson_options ) )
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

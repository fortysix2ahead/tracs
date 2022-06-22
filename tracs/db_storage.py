
from __future__ import annotations

from inspect import isfunction
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

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

	def __init__( self, path: Path=None, use_memory_storage: bool=False, access_mode: bool = 'r+', cache: bool=False, passthrough=False, factory=None, *args, **kwargs ):
		super().__init__()

		self._init_complete = False

		self._path = path
		self._access_mode = 'r' if use_memory_storage else access_mode
		self._buffering = 8192
		self._encoding = 'UTF-8'

		self._memory = MemoryStorage()
		self._use_memory_storage = use_memory_storage if path else True # auto-turn on memory mode when no path is provided

		self._use_cache = cache
		self._cache_hits = 0
		self._cache_size = 1000 if self._use_cache else 0

		self._factory = factory
		self._transformation_map: Dict[str, Union[Type, Callable]] = {}
		self._remove_null_fields: bool = True  # don't write fields which do not have a value
		self._passthrough = passthrough

	def _init( self ):
		# initialize memory if file source exists
		if self._path:
			self._memory.write( self._read_data() )

		self._init_complete = True

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		if not self._init_complete:
			self._init()

		# read data
		if self._use_memory_storage:
			data = self._memory.read()
		else:
			data = self._read_data()

		if data:
			for table_name, table_data in data.items():
				self.read_table( table_data )

		return data

	def read_table( self, table_data: Dict ) -> None:
		for item_id, item_data in dict( table_data ).items():
			if replacement := self.read_item( item_id, item_data ):
				table_data[item_id] = replacement

	def read_item( self, item_id: str, item_data: Any ) -> Optional:
		item_cls = self._factory( item_data, item_id ) if isfunction( self._factory ) else self._factory
		return item_cls( item_data, int( item_id ) ) if item_cls else None

	def _read_data( self ) -> Any:
		if self._path:
			with open( self._path, self._access_mode, self._buffering, self._encoding ) as p:
				data = p.read()
				return load_json( data if len( data ) > 0 else EMPTY_JSON )

	def write( self, data: Dict[str, Dict[str, Any]] ) -> None:
		if data:
			for table_name, table_data in data.items():
				self.write_table( table_name, table_data )

		self._memory.write( data )
		self._cache_hits += 1

		if not self._use_memory_storage:
			self.flush()

	def write_table( self, table_name: str, table_data: Dict ):
		for item_id, item_data in dict( table_data ).items():
			if replacement := self.write_item( item_id, item_data ):
				table_data[item_id] = replacement

	# noinspection PyMethodMayBeStatic
	def write_item( self, item_id: str, item: Any ) -> Optional:
		item_cls = self._factory( item, item_id ) if isfunction( self._factory ) else self._factory
		# todo: item_cls might be None and Document needs to be used
		return as_dict( item, item_cls, modify_arg=True, remove_null_fields=True )

	def flush( self, force=False ) -> None:
		if force or self._cache_hits >= self._cache_size:
			if self._path:
				self._path.write_bytes( dump_as_json( self._memory.read(), option=self.orjson_options ) )
				self._cache_hits = 0

	def close( self ) -> None:
		self.flush( force=True )

	@property
	def factory( self ) -> Callable:
		return self._factory

	@factory.setter
	def factory( self, fn: Callable ) -> None:
		self._factory = fn

	@property
	def memory( self ) -> MemoryStorage:
		return self._memory

	@property
	def transformation_map( self ):
		return self._transformation_map

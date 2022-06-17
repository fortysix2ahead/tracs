
from __future__ import annotations

from copy import deepcopy
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from orjson import loads as load_json
from orjson import dumps as dump_as_json
from orjson.orjson import OPT_APPEND_NEWLINE
from orjson.orjson import OPT_INDENT_2
from orjson.orjson import OPT_SORT_KEYS
from tinydb.storages import MemoryStorage
from tinydb.storages import Storage

log = getLogger( __name__ )

EMPTY_JSON = '{}'

class OrJSONStorage( Storage ):

	#options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS| OPT_PASSTHROUGH_SUBCLASS
	options = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

	# noinspection PyUnusedLocal
	def __init__( self, path: Path=None, use_memory_storage: bool=False, cache: bool=False, *args, **kwargs ):
		super().__init__()

		self._path = path
		self._memory_storage = MemoryStorage()
		self._use_memory_storage = use_memory_storage
		self._use_cache = cache
		self._cache = None
		self._cache_size = 1000
		self._cache_hits = 0

		if path and not path.exists():
			path.touch( exist_ok=True )

		if path:
			data = path.read_bytes()
			data = data if len( data ) > 0 else EMPTY_JSON
			json_data = load_json( data )
		else:
			json_data = {}

		if use_memory_storage:
			self._memory_storage.write( json_data )

	def read( self ) -> Optional[Dict[str, Dict[str, Any]]]:
		if self._use_memory_storage:
			data = self._memory_storage.read()
		else:
			data = self._path.read_bytes()
			data = data if len( data ) > 0 else EMPTY_JSON
			data = load_json( data )

		return data

	def write( self, data: Dict[str, Dict[str, Any]] ):
		if self._use_memory_storage:
			self._memory_storage.write( data )
		else:
			do_write = True
			# deactivate cache handling for the moment ...
			# self._cache = deepcopy( data )
			# if self._use_cache:
			# 	if self._cache_hits == self._cache_size:
			# 		self._cache_hits = 0
			# 		do_write = True
			# 	else:
			# 		self._cache_hits += 1
			# 		do_write = False
			# else:
			# 	do_write = True

			if do_write:
				self._path.write_bytes( dump_as_json( data, option=self.options ) )
				#self._path.write_bytes( dump_as_json( self._cache, option=self.options ) )

	@property
	def memory_storage( self ) -> MemoryStorage:
		return self._memory_storage

	@property
	def use_memory_storage( self ) -> bool:
		return self._use_memory_storage

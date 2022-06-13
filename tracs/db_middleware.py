
from __future__ import annotations

from inspect import isfunction
from logging import getLogger
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

from tinydb.middlewares import Middleware

from .dataclasses import as_dict

log = getLogger( __name__ )

class DataClassMiddleware( Middleware ):

	def __init__( self, storage_cls, *args, **kwargs ):
		super().__init__( storage_cls ) # Any middleware *has* to call the super constructor with storage_cls

		self._transmap: Dict[str, Union[Type, Callable]] = {}
		self._remove_null_fields: bool = True  # don't write fields which do not have a value

	def read( self ):
		if data := self.storage.read():
			for table_name, table_data in data.items():
				self.read_table( table_name, table_data )

		return data

	def read_table( self, table_name: str, table_data: Dict ) -> None:
		cls = self._transmap.get( table_name ) # find document class for the table

		# print( f'item class for table {table_name} = {cls}' )

		if table_name in self._transmap.keys():
			for item_id, item_data in dict( table_data ).items():
				if replacement := self.read_item( item_id, item_data, cls ):
					table_data[item_id] = replacement
		else:
			pass
			# print( f'table {table_name} not found in transmap, skipping process items' )

	# noinspection PyMethodMayBeStatic
	def read_item( self, item_id: str, item_data: Any, item_cls: Type ) -> Optional:
		if isfunction( item_cls ):
			item_cls = item_cls( item_data, item_id )

		if item_cls:
			# print( f'using {item_cls} as document class' )
			return item_cls( item_data, int( item_id ) )
		else:
			# print( f'no item_cls found' )
			return None

	def write( self, data ):
		if data:
			for table_name, table_data in data.items():
				self.write_table( table_name, table_data )

		self.storage.write( data )

	def write_table( self, table_name: str, table_data: Dict ):
		cls = self._transmap.get( table_name ) # find document class for the table

		# print( f'item class for table {table_name} = {cls}' )

		if table_name in self._transmap.keys():
			for item_id, item_data in dict( table_data ).items():
				if replacement := self.write_item( item_id, item_data, cls ):
					table_data[item_id] = replacement
		else:
			pass
			# print( f'table {table_name} not found in transmap, skipping process items' )

	# noinspection PyMethodMayBeStatic
	def write_item( self, item_id: str, item: Any, item_cls: Type ) -> Optional:
		if isfunction( item_cls ):
			item_cls = item_cls( item, item_id )

		return as_dict( item, item_cls, modify_arg=True, remove_null_fields=True )

	def close( self ):
		self.storage.close()

	@property
	def transmap( self ):
		return self._transmap

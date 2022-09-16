
from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import Field
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Tuple

# constants
PERSIST = 'persist'
PERSIST_AS = 'persist_as'
PROTECTED = 'protected'

class DictFilter:
	def __init__( self, remove_persist: bool = True, remove_null: bool = True, remove_data: bool = True, remove_protected: bool = False ):
		self.remove_persist = remove_persist
		self.remove_null = remove_null
		self.remove_data = remove_data
		self.remove_protected = remove_protected

	def __call__( self, f: Field, value: Any ) -> bool:
		if self.remove_persist and not f.metadata.get( PERSIST, True ):
			return True
		elif self.remove_null and value is None:
			return True
		elif self.remove_data and f.name == 'data':
			return True
		elif self.remove_protected and f.metadata.get( PROTECTED ):
			return True
		else:
			return False

# noinspection PyShadowingNames,PyUnusedLocal
def deserialize( inst: type, f: Field, value: Any ) -> Any:
	return value

#def as_dict( instance: Union[DataClass, Dict], instance_type: Type[DataClass] = None, attributes: List[Attribute] = None, modify_arg: bool = False, remove_persist: bool = True, remove_null: bool = True, remove_data = True, remove_protected = False ) -> Optional[Dict]:
def as_dict( instance: DataClass, remove_persist: bool = True, remove_null: bool = True, remove_data = True, remove_protected = False ) -> Optional[Dict]:
	# _serialize = serialize # use serializer from above
	_filter = DictFilter( remove_persist, remove_null, remove_data, remove_protected )
	_dict = asdict( instance )

	for f in fields( instance ):
		if _filter( f, _dict.get( f.name ) ):
			del _dict[f.name]

	return _dict

@dataclass( init=True )
class DataClass( MutableMapping ):

	def __post_init__( self ):
		pass # do nothing here

	# implementation of methods for mutable mapping

	def __getitem__( self, k: Any ) -> Any:
		if hasattr( self, k ): # todo: throw exception here?
			return getattr( self, k )
		else:
			return None

	def __setitem__( self, k: Any, v: Any ) -> None:
		if hasattr( self, k ): # todo: throw exception here?
			setattr( self, k, v )

	def __delitem__( self, k: Any ) -> None:
		if hasattr( self, k ): # todo: throw exception here?
			setattr( self, k, None )

	# more mapping methods

	def __contains__( self, __o: object ) -> bool:
		return hasattr( self, __o )

	def __iter__( self ) -> Iterator:
		return asdict( self ).__iter__()

	def __len__( self ) -> int:
		return asdict( self ).__len__()

	def keys( self ):
		return as_dict( self ).keys()

	def items( self ):
		return asdict( self ).items()

	def values( self ):
		return asdict( self ).values()

	def asdict( self ) -> Dict:
		return as_dict( self )

	def hasattr( self, o: str ) -> bool:
		return hasattr( self, o )

	def get( self, k: Any ) -> Any:
		return self.__getitem__( k )

	def _attr_for( self, k: Any ) -> Optional[Field]:
		return attr_for( attributes=self.__class__.__attrs_attrs__, key=k )

	def _value_for( self, k: Any ) -> Any:
		return getattr( self, k )

	def _default_for( self, k: Any ) -> Any:
		return att.default if (att := self._attr_for( k )) else None

	def _values_for( self, k: Any ) -> Tuple[Any, Any, Any]:
		"""
		For debugging only: returns the values for a provided key in the following order:
		o[key], getattr( key ), getitem( key ), get( key )

		:param k: key
		:return: tuple with four values
		"""
		_item = self[k] if k in self else None
		_getatt = getattr( self, k ) if hasattr( self, k ) else None
		_get = self.get( k )
		return _item, _getatt, _get

@dataclass( init=True )
class BaseDocument( DataClass ):

	data: Any = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )
	"""Data that makes up this dataclass, only used for initializing, set to None when init is done"""

	doc_id: int = field( default=0, metadata={ PERSIST: False, PROTECTED: True } )
	"""doc_id for tinydb compatibility"""

	id: int = field( default=0, metadata={ PERSIST: False, PROTECTED: True } )
	"""id of the document, will not be persisted as it is calculated from doc_id"""

	dirty: bool = field( default=False, repr=False, metadata={ PERSIST: False, PROTECTED: True } )
	"""flag to indicate that the document contains changes to need to be persisted"""

	def __post_init__( self ):
		super().__post_init__()

		# only set fields from data which exist, ignore the others
		if self.data:
			for f in fields( self ):
				if f.name in self.data:
					setattr( self, f.name, self.data[f.name] )

		if self.doc_id:
			self.id = self.doc_id

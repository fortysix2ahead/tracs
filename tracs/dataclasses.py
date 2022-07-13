
from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime
from datetime import time
from enum import Enum
from typing import Any, Union
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from attrs import Attribute
from attrs import asdict
from attrs import field
from attrs import define

# constants
PERSIST = 'persist'
PERSIST_AS = 'persist_as'
PROTECTED = 'protected'
ATTRS = '__attrs_attrs__'

# value serialization/deserialization

def attr_for( cls: Type = None, attributes: List[Attribute] = None, key: Any = None ):
	if cls and hasattr( cls, '__attrs_attrs__' ):
		attributes = cls.__attrs_attrs__

	for att in attributes or []:
		if att.name == key:
			return att
	return None

# noinspection PyShadowingNames,PyUnusedLocal
# todo: this serializer is far from complete and needs to be improved for recursion when there's a use case
def serialize( inst: Optional[Type], field: Optional[Attribute], value: Any ) -> Any:
	if isinstance( value, datetime ):
		return value.isoformat()
	elif isinstance( value, time ):
		return value.isoformat()
	elif isinstance( value, Enum ):
		return value.value
	elif isinstance( value, list ):
		return [ serialize( None, None, l ) for l in value ]
	elif hasattr( value, ATTRS ):
		return asdict( value )
	return value

class DictFilter:
	def __init__( self, remove_persist: bool = True, remove_null: bool = True, remove_data: bool = True, remove_protected: bool = False ):
		self.remove_persist = remove_persist
		self.remove_null = remove_null
		self.remove_data = remove_data
		self.remove_protected = remove_protected

	# from attrs documentation:
	# A callable whose return code determines whether an attribute or element is included (True) or dropped (False).
	# Is called with the attrs.Attribute as the first argument and the value as the second argument.
	def __call__( self, field: Attribute, value: Any ) -> bool:
		if self.remove_persist and not field.metadata.get( PERSIST, True ):
			return False
		elif self.remove_null and value is None:
			return False
		elif self.remove_data and field.name == 'data':
			return False
		elif self.remove_protected and field.metadata.get( PROTECTED ):
			return False
		else:
			return True

# noinspection PyShadowingNames,PyUnusedLocal
def deserialize( inst: type, field: Attribute, value: Any ) -> Any:
	return value

def as_dict( instance: Union[DataClass, Dict], instance_type: Type[DataClass] = None, attributes: List[Attribute] = None, modify_arg: bool = False, remove_persist: bool = True, remove_null: bool = True, remove_data = True, remove_protected = False ) -> Optional[Dict]:
	_serialize = serialize # use serializer from above
	_filter = DictFilter( remove_persist, remove_null, remove_data, remove_protected )

	_dict = None
	if instance and hasattr( instance.__class__, '__attrs_attrs__' ):
		_dict = asdict( instance, value_serializer=_serialize, filter=_filter )
		# deactivated serialization of additional content in data as data is always null as of now
		# if hasattr( instance, 'data' ):
		#	_dict = _dict | instance.data if instance.data else _dict # who takes precedence?

	elif instance and instance_type and hasattr( instance_type, '__attrs_attrs__' ):
		_attrs: List[Attribute] = instance_type.__attrs_attrs__ or attributes or [] # currently instance_type takes precedence
		_dict = instance if modify_arg else dict( instance ) # modify prodived dict directly?

		for f, v in dict( _dict ).items():
			if att := attr_for( attributes=_attrs, key=f ):
				if _filter and _filter( att, v ):
					_dict[f] = _serialize( instance_type, att, v )
					if PERSIST_AS in att.metadata:
						_dict[att.metadata[PERSIST_AS]] = _dict[f]
						del _dict[f]
				else:
					del _dict[f]
			# do we want to serialize dict item where no attr exists for? -> turned off at the moment
			# else:
			#	_dict[f] = _serialize( instance_type, None, v )

	if _dict and remove_null:
		for f, v in dict( _dict ).items():
			if v is None:
				del _dict[f]

	if _dict and remove_data and 'data' in _dict:
		del _dict['data']

	return _dict

# converters (example only)

# your_hook(cls: type, fields: list[attrs.Attribute]) → list[attrs.Attribute]
# usage as parameter to @define( field_transformer=auto_convert )
# noinspection PyShadowingNames,PyUnusedLocal
def transform( cls: type, fields: List[Attribute]) -> List[Attribute]:
	results = []
	for field in fields:
		if field.converter is not None:
			results.append( field )
			continue
		if field.type in { datetime, 'datetime' }:
			converter = (lambda d: datetime.fromisoformat( d ) if isinstance( d, str ) else d)
		else:
			converter = None
		results.append( field.evolve( converter=converter ) )

	return results

# field converters

# noinspection PyTypeChecker
def str2datetime( s: Union[datetime, str] ) -> datetime:
	if type( s ) is datetime:
		return s
	elif type( s ) is str:
		return datetime.fromisoformat( s )
	else:
		return None

# noinspection PyTypeChecker
def str2time( s: Union[time, str] ) -> time:
	if type( s ) is time:
		return s
	elif type( s ) is str:
		return time.fromisoformat( s )
	else:
		return None

@define( init=True )
class DataClass( MutableMapping ):

	def __attrs_post_init__( self ):
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
		return self.hasattr( str( __o ) )

	def __iter__( self ) -> Iterator:
		return asdict( self ).__iter__()

	def __len__( self ) -> int:
		return asdict( self ).__len__()

	def keys( self ):
		return asdict( self ).keys()

	def items( self ):
		return asdict( self ).items()

	def values( self ):
		return asdict( self ).values()

	def asdict( self ) -> Dict:
		return asdict( self, value_serializer=serialize, filter=DictFilter() )

	def hasattr( self, o: str ) -> bool:
		return hasattr( self, o )

	def get( self, k: Any ) -> Any:
		return self.__getitem__( k )

	def _attr_for( self, k: Any ) -> Optional[Attribute]:
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

@define( init=True )
class BaseDocument( DataClass ):

	data: Any = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	"""Data that makes up this dataclass, only used for initializing, set to None when init is done"""

	doc_id: int = field( init=True, default=0, metadata={ PERSIST: False, PROTECTED: True } )
	"""doc_id for tinydb compatibility"""

	id: int = field( init=True, default=0, metadata={ PERSIST: False, PROTECTED: True } )
	"""id of the document, will not be persisted as it is calculated from doc_id"""

	uid: str = field( init=True, default=None, metadata={ PROTECTED: True } )
	"""unique id of this document in the form of <classifier:number>"""

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.data:
			for name, value in self.data.items():
				setattr( self, name, value )

		if self.doc_id:
			self.id = self.doc_id

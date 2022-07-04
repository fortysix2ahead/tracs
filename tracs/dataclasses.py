
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

# noinspection PyShadowingNames,PyUnusedLocal
def serialize_filter( field: Attribute, value: Any ) -> bool:
	return field.metadata.get( PERSIST, True )

# noinspection PyShadowingNames,PyUnusedLocal
def deserialize( inst: type, field: Attribute, value: Any ) -> Any:
	return value

def as_dict( instance: Any, instance_type: Type = None, attributes: List[Attribute] = None, modify_arg: bool = False, remove_persist_fields: bool = True, remove_null_fields: bool = True, remove_data_field = True ) -> Optional[Dict]:
	_serialize = serialize # use serializer from above
	_filter = serialize_filter if remove_persist_fields else None # apply filter when arg is True

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

	if _dict and remove_null_fields:
		for f, v in dict( _dict ).items():
			if v is None:
				del _dict[f]

	if _dict and remove_data_field and 'data' in _dict:
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

	doc_id: int = field( init=True, default=0, metadata={ PERSIST: False, PROTECTED: True } )

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
		#return { **self.data, **asdict( self, value_serializer=serialize, filter=serialize_filter ) }
		return asdict( self, value_serializer=serialize, filter=serialize_filter )

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
	"""id of the document, will not be persisted as it is calculated from raw_id/doc_id"""

	uid: str = field( init=False, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	"""unique id of this document in the form of <classfifier>:<id or raw_id>"""

	classifier: str = field( init=True, default=None, metadata={ PROTECTED: True } )
	"""classifier of this document, used to mark documents as belonging to a certain service"""

	dataclass: str = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	"""indicator for which class is to be used when deserializing, not yet used"""

	service: str = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	"""virtual field for backward compatibility, to be removed"""

	raw: Any = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )  # raw data used for initialization from external data sources
	raw_id: int = field( init=True, default=0, metadata= { PROTECTED: True } )  # raw id as raw data might not contain all data necessary
	raw_name: str = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )  # same as raw id
	raw_data: Union[str, bytes] = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )  # serialized version of raw, can be i.e. str or bytes

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		if self.data:
			for name, value in self.data.items():
				# overwrite att if its value is the default
				if self.hasattr( name ) and getattr( self, name ) == self._attr_for( name ).default:
					setattr( self, name, value )
			self.data = None # delete data after content has been imported

		self.id = self.doc_id if self.id == self._attr_for( 'id' ).default else self.id
		self.uid = f'base:{self.id}'
		self.service = self.classifier # todo: for backward compatibility

# syntactic sugar for field

def fld( *args, **kwargs ) -> Any:
	_persist = kwargs.pop( PERSIST, False )
	_persist_as = kwargs.pop( PERSIST_AS, None )
	_protected = kwargs.pop( PROTECTED, False )
	_metadata = {
		PERSIST: _persist,
		PERSIST_AS: _persist_as,
		PROTECTED: _protected,
	}

	return field( *args, **kwargs, metadata=_metadata )

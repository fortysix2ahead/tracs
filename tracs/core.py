from __future__ import annotations

from datetime import datetime
from functools import cached_property
from sys import version_info
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, Generic, Iterator, List, Mapping, Optional, Tuple, Type, TypeVar, Union

from attr import AttrsInstance
from attrs import define, field, fields, Attribute

FIELD_KWARGS = {
	'init': True,
	'repr': True,
	'hash': True,
	'compare': True,
}

FIELD_KWARGS = FIELD_KWARGS if version_info.minor < 10 else { **FIELD_KWARGS, 'kw_only': False }

T = TypeVar('T')

@define
class Container( Generic[T] ):
	"""
	Dict-like container for activities/resources and the like. Super class to put common methods into.
	"""

	data: List[T] = field( factory=list )

	__id_map__: Dict[int, T] = field( factory=dict, init=False, alias='__id_map__' )
	__uid_map__: Dict[str, T] = field( factory=dict, init=False, alias='__uid_map__' )
	__it__: Iterator = field( default=None, init=False, alias='__it__' )

	# fill post init later
	def __attrs_post_init__( self ):
		pass

	# calculation of next id
	def __next_id__( self ) -> int:
		existing_ids = [r.id for r in self.data]
		id_range = range( 1, max( existing_ids ) + 2 ) if len( existing_ids ) > 0 else [1]
		return set( id_range ).difference( set( existing_ids ) ).pop()

	# len() support

	def __len__( self ) -> int:
		return len( self.data )

	# iteration support

	def __iter__( self ):
		self.__it__ = self.data.__iter__()
		return self.__it__

	def __next__( self ):
		return self.__it__.__next__()

	# dict-like access

	# this might be overridden in subclasses
	def __contains__( self, item: T ) -> bool:
		try:
			return any( [item.uid == r.uid for r in self.data] )
		except AttributeError:
			return False

	def __getitem__( self, key: str ):
		return self.__uid_map__[key]

	# various helpers

	def get( self, key: str ) -> Optional[T]:
		return next( (i for i in self.data if i.uid == key ), None )

	def idget( self, key: int ) -> Optional[T]:
		return next( (i for i in self.data if i.id == key ), None )

	def ids( self ) -> List[int]:
		return [r.id for r in self.data]

	def keys( self ) -> List[str]:
		return list( self.__uid_map__.keys() )

	def values( self ) -> List[T]:
		return list( self.data )

	def items( self ) -> List[Tuple[str, T]]:
		return list( self.__uid_map__.items() )

	def uid_map( self ) -> Mapping[str, T]:
		return MappingProxyType( self.__uid_map__ )

	def uid_keys( self ) -> List[str]:
		return list( self.__uid_map__.keys() )

	def id_map( self ) -> Mapping[int, T]:
		return MappingProxyType( self.__id_map__ )

	def id_keys( self ) -> List[int]:
		return list( self.__id_map__.keys() )

	# content access

	def all( self, sort=False ) -> List[T]:
		# todo: we could also sort by id, not str( id )
		return list( self.data ) if not sort else sorted( self.data, key=lambda r: str( r.id ) )

	# content modification, check if this can be generalized

	def add( self, *items: Union[T, List[T]] ) -> List[int]:
		pass

	def update( self, *items: Union[T, List[T]] ) -> Tuple[List[int], List[int]]:
		pass

@define( init=False )
class Metadata:

	uid: str = field( default=None )
	created: datetime = field( default=None )
	modified: datetime = field( default=None )

	__fields__: Dict[str, Any] = field( factory=dict, alias='__fields__' )
	# __kwargs__: Dict[str, Any] = field( factory=dict, alias='__kwargs__' )

	@cached_property
	def __fieldnames( self ) -> List[str]:
		return [f.name for f in fields( self.__class__ )]

	@cached_property
	def __regular_fieldnames( self ) -> List[str]:
		return [f.name for f in fields( self.__class__ ) if not f.name.startswith( '__' )]

	# noinspection PyUnresolvedReferences
	def __init__( self, *args, **kwargs ):
		self.__attrs_init__( *args, **{ k: v for k, v in kwargs.items() if k in self.__fieldnames } )
		self.__fields__ = { k: v for k, v in kwargs.items() if k not in self.__fieldnames }

	# len() support

	def __len__( self ) -> int:
		return len( self.__fields__ ) + len( self.__regular_fieldnames )

	# getter

	def __getattr__( self, key: str ) -> Any:
		if key in self.__fieldnames:
			return super().__getattribute__( key )
		else:
			return self.__fields__.get( key )

	def __getitem__( self, key: str ):
		return self.__getattr__( key )

	# setter

	def __setitem__( self, key: str, value: Any ) -> None:
		self.__setattr__( key, value )

	def __setattr__( self, key, value ):
		if key in self.__fieldnames:
			super().__setattr__( key, value )
		else:
			self.__fields__[key] = value

	# dict-like methods

	def keys( self ) -> List[str]:
		return [ *self.__regular_fieldnames, *self.__fields__.keys() ]

	def values( self ) -> List[Any]:
		return [ *[self.__getattr__( f ) for f in self.__regular_fieldnames], *self.__fields__.values() ]

	def items( self ) -> List[Tuple[str, Any]]:
		return [ *[( f, self.__getattr__( f ) ) for f in self.__regular_fieldnames ], *self.__fields__.items() ]

	def as_dict( self ) -> Dict[str, Any]:
		return { f: self.__getattr__( f ) for f in self.__regular_fieldnames } | self.__fields__

@define
class VirtualField:

	name: str = field( default=None )
	type: Type = field( default=None )
	default: Any = field( default=None )
	factory: Callable = field( default=None )
	description: str = field( default=None )
	display_name: str = field( default=None )

	def __call__( self, parent: Any = None ) -> Any:
		return self.value_for( parent )

	def value_for( self, parent: Any = None ) -> Any:
		if self.default:
			return self.default
		elif self.factory:
			return self.factory( parent )
		else:
			raise AttributeError( f'virtual field {self.name} has neither a default nor a factory' )

@define( slots=False )
class VirtualFields:

	__fields__: Dict[str, VirtualField] = field( factory=dict, alias='__fields__' )
	__parent__: Any = field( default=None, alias='__parent__' )

	def __call__( self, parent: Any ) -> VirtualFields:
		if parent is None:
			raise ValueError( 'VirtualFields instance cannot be used without a parent instance' )

		self.__parent__ = parent
		return self

	def __getattr__( self, name: str ) -> Any:
		if name in self.__fields__:
			return self.__fields__.get( name )( self.__parent__ )
		else:
			return self.__parent__.__getattribute__( name )

	def __contains__( self, item ) -> bool:
		return item in self.__fields__.keys()

	def __getitem__( self, key: str ) -> VirtualField:
		return self.__fields__[key]

	def __setitem__( self, key: str, field: VirtualField ) -> None:
		if not isinstance( field, VirtualField ):
			raise ValueError( f'value must be of type {VirtualField}' )

		self.__fields__[key] = field

	def add( self, field: VirtualField ) -> None:
		self.__fields__[field.name] = field

	def set_field( self, name: str, vf: VirtualField ) -> None:
		self.__fields__[name] = vf

	def items( self ):
		return self.__fields__.items()

@define
class VirtualFieldsBase( AttrsInstance ):

	__vf__: ClassVar[VirtualFields] = VirtualFields()

	@classmethod
	def VF( cls ) -> VirtualFields:
		return cls.__vf__

	@classmethod
	def fields( cls, include_internal = True, include_virtual = False ) -> List[Attribute | VirtualField]:
		_fields = list( fields( cls ) )
		if include_virtual:
			_fields.extend( [f for f in cls.__vf__.__fields__.values()] )
		if not include_internal:
			_fields = list( filter( lambda f: not f.name.startswith( '_' ), _fields ) )
		return _fields

	@classmethod
	def field_names( cls, include_internal = True, include_virtual = False ) -> List[str]:
		return [f.name for f in cls.fields( include_internal=include_internal, include_virtual=include_virtual )]

	@classmethod
	def field_type( cls, field_name: str ) -> Any:
		if f := next( (f for f in cls.fields( include_internal=True, include_virtual=True ) if f.name == field_name), None ):
			return f.type
		else:
			return None

	@property
	def vf( self ) -> VirtualFields:
		return self.__class__.__vf__( self )

@define
class FormattedField:

	name: str = field( default=None )
	formatter: Callable = field( default=None )
	format: str = field( default=None )
	locale: str = field( default=None )

	def __call__( self, value: Any ) -> Any:
		return self.__format__( value )

	def __format__( self, value: Any ) -> Any:
		return self.formatter( value, self.format, self.locale )

@define( slots=False )
class FormattedFields:

	__fields__: Dict[str, FormattedField] = field( factory=dict, alias='__fields__' )
	__parent_cls__: Type = field( default=None, alias='__parent_cls__' )
	__parent__: Any = field( default=None, alias='__parent__' )

	def __call__( self, parent: Any ) -> FormattedFields:
		if parent is None:
			raise AttributeError( 'FormattedFields instance cannot be used without a parent instance' )

		self.__parent__ = parent
		return self

	def __getattr__( self, name: str ) -> Any:
		if self.__parent__ is None:
			raise AttributeError( 'FormattedFields instance cannot be used without a parent instance' )

		if name in self.__fields__:
			return self.__fields__.get( name )( getattr( self.__parent__, name ) )
		else:
			# todo: this return the parent value, we could also call str( value ) here instead, to be decided later
			return getattr( self.__parent__, name )

	def __getitem__( self, key: str ) -> FormattedField:
		return self.__fields__[key]

	def __setitem__( self, key: str, field: FormattedField | Callable ) -> None:
		if not callable( field ):
			raise ValueError( f'value must be of type {FormattedField} or Callable' )

		if not isinstance( field, FormattedField ):
			field = FormattedField( name=key, formatter=field )

		self.__fields__[key] = field

	def add( self, field: FormattedField ) -> None:
		self[field.name] = field

	def as_list( self, *fields: str, suppress_error: bool = False, converter: Callable = None ) -> List[str]:
		results = []
		if suppress_error:
			for f in fields:
				try:
					results.append( getattr( self, f ) )
				except AttributeError:
					results.append( None )
		else:
			results = [ getattr( self, f ) for f in fields ]

		results = [ converter( r ) for r in results ] if converter else results
		return results

	@property
	def fields( self ) -> Dict[str, Union[FormattedField, Callable]]:
		return self.__fields__

	@property
	def parent( self ) -> Any:
		return self.__parent__

	@property
	def parent_cls( self ) -> Type:
		return self.__parent_cls__

@define
class FormattedFieldsBase( AttrsInstance ):

	__fmf__: ClassVar[FormattedFields] = FormattedFields()

	@classmethod
	def FMF( cls ) -> FormattedFields:
		return cls.__fmf__

	@property
	def fmf( self ) -> FormattedFields:
		return self.__class__.__fmf__( self )

@define
class Keyword:

	name: str = field( default=None )
	description: Optional[str] = field( default=None )
	expr: str = field( default=None )
	fn: Callable = field( default=None )

	def __call__( self, *args, **kwargs ) -> str:
		if self.expr:
			return self.expr
		elif self.fn:
			return self.fn()
		else:
			raise TypeError( f'unable to call keyword {self.name}, neither expr or fn have appropriate values' )

@define
class Normalizer:

	name: str = field( default=None )
	type: Any = field( default=None )
	description: Optional[str] = field( default=None )
	fn: Callable = field( default=None )

	def __call__( self, *args, **kwargs ) -> str:
		return self.fn( *args, **kwargs )

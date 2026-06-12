from __future__ import annotations

from collections import UserDict
from datetime import datetime
from functools import cached_property
from logging import getLogger
from sys import version_info
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, Generic, Iterator, List, Mapping, Optional, Tuple, Type, TypeVar, Union

from attr import AttrsInstance
from attrs import Attribute, define, field, fields, NOTHING
from attrs.setters import NO_OP
from dateutil.tz import UTC

from tracs.uid import UID

log = getLogger( __name__ )

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

@define
class Metadata:

	created: Optional[datetime] = field( default=None )
	"""Timestamp of creation.
	"""
	modified: Optional[datetime] = field( default=None )
	"""Timestamp of last modification.
	"""

	favourite: bool = field( default=False )
	"""Marker that this activity is a favourite one.
	"""

	member_of: UID = field( default=None )
	"""Indicator that an activity is a member of a group.
	There can only be one parent activity, activities part of multiple groups do not make sense.
	"""
	members: List[UID] = field( factory=list )
	"""List of group members.
	"""

	part_of: List[UID] = field( factory=list )
	"""Indicator that an activity is part of one or multiple other activities.
	"""
	parts: List[UID] = field( factory=list )
	"""List of parts of this activity. Only applies to multipart activities.
	"""

	aux: Dict[str, str] = field( factory=dict )
	"""Additional, not predefined metadata.
	"""

	def __attrs_post_init__( self ):
		# todo: enable this later
		# self.created = self.created if self.created else datetime.now( UTC )
		pass

	def __getitem__( self, item ):
		return self.aux[item]

	def set( self, key: str, value: Any ) -> None:
		try:
			setattr( self, key, value )
		except AttributeError:
			self.aux[key] = value
		finally:
			self.modified = datetime.now( UTC )
			# todo: remove, when create above has been enabled
			if not self.created:
				self.created = self.modified

	def keys( self ):
		return self.aux.keys()

	def values( self ):
		return self.aux.values()

	def items( self ):
		return self.aux.items()

	def all_keys( self ) -> List[str]:
		return [k for k in [*self.__fields__, *self.keys()]]

	def all_values( self ) -> List[str]:
		return [v for v in [*self.__values__, *self.values()]]

	def all_items( self ) -> Dict[str, str]:
		return (self.__items__ | dict( self.items() )).items()

	@cached_property
	def __fields__( self ) -> List[str]:
		return [f.name for f in fields( self.__class__ ) if f.name != 'aux' ]

	@cached_property
	def __values__( self ) -> List[str]:
		return [getattr( self, f ) for f in self.__fields__]

	@cached_property
	def __items__( self ) -> Dict[str, str]:
		return { f: getattr( self, f ) for f in self.__fields__ }

# Derived field for extending Activity

@define
class DerivedField:

	name: str = field( default=None )
	type: Type = field( default=None )
	fn: Callable = field( default=None )
	description: str = field( default=None )
	display_name: str = field( default=None )
	expose: bool = field( default=True )

# noinspection PyShadowingNames
def augment( cls: Type, field: DerivedField, ignore_errors: bool = True ) -> Type:
	if hasattr( cls, field.name ):
		if ignore_errors:
			log.warning( f'overwriting Activity fields is not supported: field "{field.name}" already exists' )
		else:
			raise AttributeError( f'overwriting Activity fields is not supported: field "{field.name}" already exists' )

	# augment provided class with property
	setattr( cls, field.name, property( fget=field.fn ) )

	# noinspection PyArgumentList
	derived_attr = Attribute(
		name=field.name,
		default=NOTHING,
		validator=None,
		repr=False, # exclude from repr
		cmp=None, # exclude from cmp
		eq=False, # exclude from eq
		eq_key=None,
		order=False,
		order_key=None,
		hash=False,
		init=False, # exclude from in __init__
		metadata={ 'derived': True, 'exposed': field.expose },
		type=field.type,
		converter=None,
		kw_only=False,
		inherited=False,
		on_setattr=NO_OP,
		alias=field.name,
	)

	cls.__attrs_attrs__ = cls.__attrs_attrs__ + (derived_attr,)

def fields_of( obj: Type[AttrsInstance]|AttrsInstance, include_internal: bool = False, include_unexposed: bool = False ) -> List[Attribute]:
	_fields = fields( obj )
	_fields = list( filter( lambda f: include_internal and f.name.startswith( '_' ) or not f.name.startswith( '_' ), _fields ) )
	_fields = list( filter( lambda f: include_unexposed and f.metadata.get( 'exposed' ) is False or f.metadata.get( 'exposed', True ) is True, _fields ) )
	return _fields

def derived_fields_of( obj: Type[AttrsInstance]|AttrsInstance, include_internal: bool = False ) -> List[Attribute]:
	return [ f for f in fields_of( obj, include_internal ) if f.metadata.get( 'derived' ) is True ]

def field_names( obj: Type[AttrsInstance]|AttrsInstance, include_internal: bool = False, include_unexposed: bool = False ) -> List[str]:
	return [f.name for f in fields_of( obj, include_internal, include_unexposed )]

def derived_field_names( obj: Type[AttrsInstance]|AttrsInstance, include_internal: bool = False, include_unexposed: bool = False ) -> List[str]:
	return [f.name for f in derived_fields_of( obj, include_internal )]

def is_derived( obj: Type[AttrsInstance]|AttrsInstance, field: str ) -> bool:
	return any( f for f in fields( obj ) if f.name == field and f.metadata.get( 'derived' ) is True )

def is_exposed( obj: Type[AttrsInstance]|AttrsInstance, field: str ) -> bool:
	return any( f for f in fields( obj ) if f.name == field and f.metadata.get( 'exposed' ) is True )

def is_internal( obj: Type[AttrsInstance]|AttrsInstance, field: str ) -> bool:
	return any( f for f in fields( obj ) if f.name == field and f.name.startswith( '_' ) )

#

@define
class FieldFormatter:

	name: str = field( default=None )
	format: str = field( default=None )
	locale: str = field( default=None )

	formatter: Callable = field( default=None )

	# noinspection PyShadowingBuiltins
	def __call__( self, value: Any, format: Optional[str] = None, locale: Optional[str] = None ) -> Any:
		return self.__format__( value, format, locale )

	# noinspection PyShadowingBuiltins
	def __format__( self, value: Any, format: Optional[str] = None, locale: Optional[str] = None ) -> Any:
		return self.formatter( value, format or self.format, locale or self.locale )

class FieldFormatters( UserDict[str, FieldFormatter] ):

	__default_formatter_name__: ClassVar[str] = '__default__'
	__default_formatter__: ClassVar[FieldFormatter] = FieldFormatter( __default_formatter_name__, formatter=lambda v, f, l: str( v ) )

	__proxy__: Any = field( default=None, alias='__proxy__' )

	def __init__( self, d: dict = None, proxy: Any = None ):
		super().__init__( d )
		self.__proxy__: Any = proxy

	def add( self, field: FieldFormatter ) -> None:
		self.data[field.name] = field

	def add_all( self, *fmf: FieldFormatter ) -> None:
		[self.add( f ) for f in fmf]

	def set( self, key: str, field: FieldFormatter ) -> None:
		self.data[key] = field

	def format( self, value: Any, name: Optional[str] = None,
	            fmt: Optional[str] = None, locale: Optional[str] = None,
	            suppress_errors: bool = False ) -> str:
		if not (formatter := self.get( name )):
			formatter = self.__class__.__default_formatter__

		try:
			return formatter( value, fmt, locale )
		except Exception as e:
			if suppress_errors:
				return ''
			else:
				raise e

	def format_attr( self, obj: Any, name: str,
	            fmt: Optional[str] = None, locale: Optional[str] = None,
	            suppress_errors: bool = False ) -> str:
		try:
			return self.format( getattr( obj, name ), name, fmt, locale, suppress_errors )
		except AttributeError as e:
			if suppress_errors:
				return ''
			else:
				raise e

	def format_fields( self, obj: Any, *fields, fmt: Optional[str] = None,
	                   locale: Optional[str] = None, suppress_errors: bool = False ) -> Tuple[str, ...]:
		return tuple( [self.format_attr( obj, f, fmt, locale, suppress_errors=suppress_errors ) for f in fields] )

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

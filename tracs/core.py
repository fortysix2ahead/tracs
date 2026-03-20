from __future__ import annotations

from collections import UserDict
from datetime import datetime
from functools import cached_property
from inspect import getmembers, signature
from logging import getLogger
from sys import version_info
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, Generic, Iterator, List, Mapping, Optional, Tuple, Type, TypeVar, Union

from attr import AttrsInstance
from attrs import Attribute, define, field, fields
from cattrs import Converter, GenConverter
from dateutil.tz import UTC

from tracs.uid import UID
from tracs.utils import fromisoformat, toisoformat

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

@define
class VirtualField:

	name: str = field( default=None )
	type: Type = field( default=None )
	default: Any = field( default=None )
	factory: Callable = field( default=None )
	description: str = field( default=None )
	display_name: str = field( default=None )
	expose: bool = field( default=True ) # expose field as regular property

	def __call__( self, parent: Any = None ) -> Any:
		return self.value_for( parent )

	def __hash__( self ):
		return hash( self.name )

	def value_for( self, parent: Any = None ) -> Any:
		if self.default:
			return self.default
		elif self.factory:
			return self.factory( parent )
		else:
			raise AttributeError( f'virtual field {self.name} has neither a default nor a factory' )

class VirtualFields( UserDict[str, VirtualField] ):

	def __init__( self, d: dict = None, proxy: Any = None ):
		super().__init__( d )
		self.__proxy__: Any = proxy

	@classmethod
	def augment( self, cls: Type ):
		for f in cls.virtual_fields().fields():
			if f.default:
				setattr( cls, f.name, property( lambda obj: f.default ) )
			elif f.factory:
				setattr( cls, f.name, property( f.factory ) )
			else:
				log.warning( f'unable to augment class {cls} with property {f.name}, neither default value nor factory exists' )

	def add( self, vf: VirtualField ) -> None:
		self.data[vf.name] = vf

	def add_all( self, *vf: VirtualField ) -> None:
		[ self.add( field ) for field in vf ]

	def set( self, vf: VirtualField ) -> None:
		self.data[vf.name] = vf

	def fields( self, include_internal: bool = False, include_unexposed: bool = False ) -> List[Attribute | VirtualField]:
		_all_fields = self.data.values()
		_regular_fields = [f for f in _all_fields if not f.name.startswith( '_' ) and f.expose]
		_internal_fields = [f for f in _all_fields if f.name.startswith( '_' ) ]
		_unexposed_fields = [f for f in _all_fields if not f.expose ]

		_fields = [ *_regular_fields ]
		if include_internal:
			_fields = [ *_fields, *_internal_fields ]
		if include_unexposed:
			_fields = [ *_fields, *_unexposed_fields ]

		return [ *set( _fields ) ]

	def field_names( cls, include_internal: bool = False, include_unexposed: bool = False ) -> List[str]:
		return [f.name for f in cls.fields( include_internal, include_unexposed )]

	def field_type( cls, field_name: str ) -> Any:
		if f := next( (f for f in cls.fields( True, True ) if f.name == field_name), None ):
			return f.type
		else:
			return None

	def value( self, field: str, inst: Any = None, quiet: bool = False ) -> Any:
		# use proxied object if available
		inst = self.__proxy__ if self.__proxy__ else inst

		if f := self.data.get( field ):
			if f.default is not None:
				return f.default
			elif f.factory is not None:
				return f.factory( inst )

		if not quiet:
			raise AttributeError()

	def values( self, *field_names: str, inst: Any = None ) -> List[Any]:
		return [ self.value( f, inst, quiet=True ) for f in field_names ]

	@property
	def vf( self ) -> VirtualFields:
		return self.__class__.__vf__.proxy( self )

@define
class FieldFormatter:

	name: str = field( default=None )
	format: str = field( default=None )
	locale: str = field( default=None )

	formatter: Callable = field( default=None )

	def __call__( self, value: Any, format: str = None, locale: str = None ) -> Any:
		return self.__format__( value, format, locale )

	def __format__( self, value: Any, format: str = None, locale: str = None ) -> Any:
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

	def format( self, name: str, fmt: str = None, locale: str = None, suppress_errors: bool = False ) -> str:
		if not (formatter := self.get( name )):
			formatter = self.__class__.__default_formatter__

		if suppress_errors:
			try:
				return formatter( getattr( self.__proxy__, name ), fmt, locale )
			except Exception:
				return ''
		else:
			return formatter( getattr( self.__proxy__, name ), fmt, locale )

	def format_as_list( self, *fields, fmt: str = None, locale: str = None, conv: Callable = None, suppress_errors: bool = False ) -> List[str]:
		if conv:
			return [conv( getattr( self.__proxy__, f ) ) for f in fields]
		else:
			return [self.format( f, fmt, locale, suppress_errors ) for f in fields]

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

from __future__ import annotations

from dataclasses import dataclass
from sys import version_info
from typing import Any, Callable, Dict, Optional, Type, Union

from attrs import define, field

FIELD_KWARGS = {
	'init': True,
	'repr': True,
	'hash': True,
	'compare': True,
}

FIELD_KWARGS = FIELD_KWARGS if version_info.minor < 10 else { **FIELD_KWARGS, 'kw_only': False }

@define
class VirtualField:

	name: str = field( default=None )
	type: Type = field( default=None )
	default: Any = field( default=None )
	factory: Callable = field( default=None )
	description: str = field( default=None )
	display_name: str = field( default=None )

	def __call__( self, value: Any = None ) -> Any:
		return self.value_for( value )

	def value_for( self, value: Any = None ) -> Any:
		if self.default:
			return self.default
		elif self.factory:
			return self.factory( value )
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

@define
class FormattedField:

	name: str = field( default=None )
	formatter: Callable = field( default=None )

	def __call__( self, value: Any ) -> Any:
		return self.format( value )

	def format( self, value: Any ) -> Any:
		return self.formatter( value )

@define
class FormattedFields:

	__fields__: Dict[str, Union[FormattedField, Callable]] = field( factory=dict, alias='__fields__' )
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
			return getattr( self.__parent__, name )

	@property
	def fields( self ) -> Dict[str, Union[FormattedField, Callable]]:
		return self.__fields__

	@property
	def parent( self ) -> Any:
		return self.__parent__

	@property
	def parent_cls( self ) -> Type:
		return self.__parent_cls__

@dataclass
class Keyword:

	name: str = field( default=None )
	description: Optional[str] = field( default=None )
	expr: Union[str, Callable] = field( default=None )

	def __call__( self, *args, **kwargs ) -> str:
		# return self.expr if type( self.expr ) is str else self.expr( *args, **kwargs )
		return self.expr if type( self.expr ) is str else self.expr()

@dataclass
class Normalizer:

	name: str = field( default=None )
	type: Any = field( default=None )
	description: Optional[str] = field( default=None )
	fn: Callable = field( default=None )

	def __call__( self, *args, **kwargs ) -> str:
		return self.fn( *args, **kwargs )

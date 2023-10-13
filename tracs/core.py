from __future__ import annotations

from dataclasses import dataclass, Field, field
from sys import version_info
from typing import Any, Callable, ClassVar, Dict, Optional, Type, Union

from attrs import define, field as attrsfield

FIELD_KWARGS = {
	'init': True,
	'repr': True,
	'hash': True,
	'compare': True,
}

FIELD_KWARGS = FIELD_KWARGS if version_info.minor < 10 else { **FIELD_KWARGS, 'kw_only': False }

class VirtualField( Field ):

	# noinspection PyShadowingBuiltins
	def __init__( self, default: Any, default_factory: Callable, name: str, type: Any, display_name: str, description: str ):
		super().__init__(
			default = default, default_factory = default_factory, **FIELD_KWARGS,
			metadata = {
				'description': description,
				'display_name': display_name,
			},
		)
		self.name = name
		self.type = type

	def __call__( self, *args, **kwargs ):
		if self.default is not None:
			return self.default
		elif self.default_factory is not None:
			return self.default_factory( *args, **kwargs )
		else:
			raise AttributeError( f'error accessing virtual field {self.name}, field has neither default or default_factory' )

	@property
	def description( self ):
		return self.metadata.get( 'description' )

	@property
	def display_name( self ):
		return self.metadata.get( 'display_name' )

@dataclass
class VirtualFields:

	__fields__: ClassVar[Dict[str, VirtualField]] = field( default={} )
	__parent__: Any = field( default=None )
	# __values__: Dict[str, VirtualField] = field( default_factory=dict ) # not used yet, we might include custom values later

	def __getattr__( self, name: str ) -> Any:
		# not used yet, see above
		# if name in self.__values__:
		#	return self.__values__.get( name )
		if name in self.__class__.__fields__:
			return self.__class__.__fields__.get( name )( self.__parent__ )
		else:
			return super().__getattribute__( name )

	def __contains__( self, item ) -> bool:
		return item in self.__fields__.keys()

@define
class FormattedField:

	name: str = attrsfield( default=None )
	formatter: Callable = attrsfield( default=None )

	def __call__( self, value: Any ) -> Any:
		return self.format( value )

	def format( self, value: Any ) -> Any:
		return self.formatter( value )

@define
class FormattedFields:

	__fields__: Dict[str, Union[FormattedField, Callable]] = attrsfield( factory=dict, alias='__fields__' )
	__parent_cls__: Type = attrsfield( default=None, alias='__parent_cls__' )
	__parent__: Any = attrsfield( default=None, alias='__parent__' )

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

# noinspection PyShadowingBuiltins
def vfield( name: str, type: Any = None, default: Any = None, display_name: Optional[str] = None, description: Optional[str] = None ) -> VirtualField:
	default, factory = (None, default) if isinstance( default, Callable ) else (default, None)
	return VirtualField(
		default=default,
		default_factory=factory,
		name=name,
		type=type,
		display_name=display_name,
		description=description
	)

from __future__ import annotations

from sys import version_info
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

from attr import AttrsInstance
from attrs import define, field, fields, Attribute

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

	def as_list( self, *fields: str, suppress_error: bool = False ) -> List[str]:
		if suppress_error:
			rval = []
			for f in fields:
				try:
					rval.append( getattr( self, f ) )
				except AttributeError:
					rval.append( None )
			return rval
		else:
			return [ getattr( self, f ) for f in fields ]

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

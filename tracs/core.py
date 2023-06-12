from dataclasses import dataclass, Field, field
from typing import Any, Callable, ClassVar, Dict, Optional

class VirtualField( Field ):

	# noinspection PyShadowingBuiltins
	def __init__( self, default: Any, default_factory: Callable, name: str, type: Any, display_name: str, description: str ):
		super().__init__(
			default = default,
			default_factory = default_factory,
			init = True,
			repr = True,
			hash = True,
			compare = True,
			metadata = {
				'description': description,
				'display_name': display_name,
			},
#			kw_only=False
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
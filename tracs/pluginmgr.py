
from __future__ import annotations

from importlib import import_module
from inspect import currentframe, FrameInfo, getmembers, isclass, signature as getsignature
from logging import getLogger
from pkgutil import extend_path, iter_modules
from types import ModuleType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from attrs import define, field
from fs.osfs import OSFS

log = getLogger( __name__ )

factory_plugins = [ 'csv', 'json', 'xml', 'gpx', 'tcx' ]

@define
class Decorator:

	fncls: Callable|Type = field( default=None )
	args: Tuple = field( factory=tuple )
	kwargs: Dict = field( factory=dict )
	frame = field( default=None )
	name: str = field( default=None )

	def __attrs_post_init__( self ):
		self.name = self.caller_name # automatically set name

	@property
	def caller_name( self ) -> str|None:
		try:
			return self.frame.f_code.co_name
		except AttributeError:
			return None

class PluginManager:

	plugins: ClassVar[Dict[str, ModuleType]] = {}
	decorators: ClassVar[List[Decorator]] = []

	importers: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	keywords: ClassVar[List[Tuple]] = []
	normalizers: ClassVar[List[Tuple]] = []
	resource_types: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	services: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	setups: ClassVar[List[Tuple]] = []
	virtual_fields: ClassVar[List[Tuple]] = []

	@classmethod
	def init( cls, plugin_paths: Optional[List[str]] = None, reinit: bool = False ):
		# this is just for debug/dev purposes
		if reinit:
			log.debug( f'clearing plugin manager content' )
			cls.plugins.clear()
			cls.decorators.clear()

		# noinspection PyUnresolvedReferences
		import tracs.plugins

		# import factory plugins
		for fp in factory_plugins:
			log.debug( f'importing factory plugin [bold green]{fp}[/bold green]' )
			cls.plugins[fp] = import_module( f'tracs.plugins.{fp}' )

		# extend plugin path and load additional, non-optional plugins
		for pp in plugin_paths or []:
			plugin_path = OSFS( root_path=pp, expand_vars=True ).getsyspath( '/tracs/plugins' )
			tracs.plugins.__path__ = extend_path( [plugin_path], 'tracs.plugins' )

		for finder, name, ispkg in iter_modules( tracs.plugins.__path__ ):
			if name not in factory_plugins:
				log.debug( f'importing plugin [bold green]{name}[/bold green] from {finder.path}' )
				cls.plugins[name] = import_module( f'tracs.plugins.{name}' )

	@classmethod
	def add_decorator( cls, fncls: Callable|Type, args: Tuple, kwargs: Dict, frame: FrameInfo = None ) -> Decorator:
		cls.decorators.append( dec := Decorator( fncls, args, kwargs, frame ) )
		return dec

def _lname( fncls: Union[Callable, Type] ) -> str:
	return fncls.__name__.lower()

def _qname( fncls: Union[Callable, Type] ) -> str:
	return f'{fncls.__module__}.{fncls.__name__}'

def _params( fncls: Union[Callable, Type] ) -> Tuple[Mapping, Any]:
	return getsignature( fncls ).parameters, next( (m[1].get( 'return' ) for m in getmembers( fncls ) if m[0] == '__annotations__'), None )

def _fnspec( fncls: Union[Callable, Type] ) -> Tuple[str, str, str, Mapping, Any]:
	"""
	Helper for examining a provided function. Returns a tuple containing
	(function name, module name, qualified name, return value type)

	:param fncls: function to be examined
	:return: tuple
	"""
	members, signature = getmembers( fncls ), getsignature( fncls )
	name = fncls.__name__
	module = fncls.__module__
	qname = f'{fncls.__module__}.{fncls.__name__}'
	params = signature.parameters
	rval = next( (m[1].get( 'return' ) for m in members if m[0] == '__annotations__'), None )
	return name, module, qname, params, rval

# decorators

def _register( *args, **kwargs ) -> Callable:
	_current_frame = kwargs.pop( '_current_frame', None )

	def _inner( fncls ):
		if fncls is not None:
			# noinspection PyShadowingNames
			dec = PluginManager.add_decorator( fncls, args, kwargs, _current_frame )
			log.debug( f'registered {dec.name} function/class from {fncls} in module {_fnspec( fncls )[1]}' )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		dec = PluginManager.add_decorator( args[0], (), {}, _current_frame )
		log.debug( f'registered {dec.name} function from {args[0]} in module {_fnspec( args[0] )[1]}' )

		if isclass( args[0] ):
			return args[0]

	return _inner

# actual real-world decorators below

def keyword( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def normalizer( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def virtualfield( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def importer( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def resourcetype( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def service( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def setup( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

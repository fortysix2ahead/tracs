
from __future__ import annotations

from importlib import import_module
from inspect import currentframe, FrameInfo, getmembers, isclass, signature as getsignature
from logging import getLogger
from pkgutil import extend_path, iter_modules
from types import ModuleType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from attrs import define, field
from fs.osfs import OSFS

from tracs.core import Keyword

log = getLogger( __name__ )

@define
class Decorator:

	fncls: Callable|Type = field( default=None )
	args: Tuple = field( factory=tuple )
	kwargs: Dict = field( factory=dict )
	frame = field( default=None )
	clazz = field( default=None )

	name: str = field( default=None )
	type: str = field( default=None )

	def __attrs_post_init__( self ):
		self.name = self.lname
		self.type = self.caller_name # automatically set type

	def __call__( self, *args, **kwargs ) -> Any:
		return self.fncls( *args, **kwargs )

	@property
	def caller_name( self ) -> str|None:
		try:
			return self.frame.f_code.co_name
		except AttributeError:
			return None

	@property
	def lname( self ) -> str:
		return self.fncls.__name__.lower()

	@property
	def module( self ) -> str:
		return self.fncls.__module__

	@property
	def qname( self ) -> str:
		return f'{self.fncls.__module__}.{self.fncls.__name__}'

	@property
	def params( self ) -> Tuple[Mapping, Any]:
		return getsignature( self.fncls ).parameters, next( (m[1].get( 'return' ) for m in getmembers( self.fncls ) if m[0] == '__annotations__'), None )

	@property
	def spec( self ) -> Tuple[str, str, str, Mapping, Any]:
		"""
		Helper for examining a provided function. Returns a tuple containing
		(function name, module name, qualified name, return value type)

		:param fncls: function to be examined
		:return: tuple
		"""
		members, signature = getmembers( self.fncls ), getsignature( self.fncls )
		name = self.fncls.__name__
		module = self.fncls.__module__
		qname = f'{self.fncls.__module__}.{self.fncls.__name__}'
		params = signature.parameters
		rval = next( (m[1].get( 'return' ) for m in members if m[0] == '__annotations__'), None )
		return name, module, qname, params, rval

@define
class Registry:

	_keyword: Dict[str, Keyword] = field( factory=dict, alias='_keyword' )
	_normalizer: Dict[str, Keyword] = field( factory=dict, alias='_normalizer' )

class PluginManager:

	plugins: ClassVar[Dict[str, ModuleType]] = {}
	decorators: ClassVar[List[Decorator]] = []

	_registry: ClassVar[Registry] = Registry()

	@classmethod
	def init( cls, plugin_paths: Optional[List[str]] = None, reinit: bool = False ):
		# this is just for debug/dev purposes
		if reinit:
			log.debug( f'clearing plugin manager content' )
			cls.plugins.clear()
			cls.decorators.clear()

		# noinspection PyUnresolvedReferences
		import tracs.plugins

		# extend plugin path and load additional, non-optional plugins
		for pp in plugin_paths or []:
			plugin_path = OSFS( root_path=pp, expand_vars=True ).getsyspath( '/tracs/plugins' )
			tracs.plugins.__path__ = extend_path( [plugin_path], 'tracs.plugins' )
			log.debug( f'adding {plugin_path} to list of plugin search paths' )

		# load plugin modules
		for finder, name, ispkg in iter_modules( tracs.plugins.__path__ ):
			try:
				cls.plugins[name] = import_module( f'tracs.plugins.{name}' )
			except ImportError:
				log.error( f'failed to import module tracs.plugins.{name}', exc_info=True )
				continue

	@classmethod
	def registry( cls ) -> Registry:
		for decorator_type in [ 'keyword', 'normalizer' ]:
			for d in filter( lambda dec:  dec.type == decorator_type, cls.decorators ):
				try:
					inst = d()
					getattr( cls._registry, f'_{d.type}' )[d.name] = inst
					log.debug( f'registered {inst} provided by decorated function/class {d.fncls}' )

				except AttributeError: # need to be extended
					log.error( f'error calling decorated object {d.fncls}' )

		return cls._registry

	@classmethod
	def register_decorator( cls, fncls: Callable | Type, args: Tuple, kwargs: Dict, frame: FrameInfo = None, clazz: Type = None ) -> Decorator:
		cls.decorators.append( d := Decorator( fncls, args, kwargs, frame, clazz ) )
		log.debug( f'registered decorator [green]{d.name}[/green] from {d.fncls} in module [green]{d.module}[/green]' )
		return d

# decorators

def _register( *args, **kwargs ) -> Callable:
	_class = kwargs.pop( '_class', None )
	_current_frame = kwargs.pop( '_current_frame', None )

	def _inner( fncls ):
		if fncls is not None:
			PluginManager.register_decorator( fncls, args, kwargs, _current_frame, _class )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		PluginManager.register_decorator( args[0], (), {}, _current_frame, _class )
		if isclass( args[0] ):
			return args[0]

	return _inner

# actual real-world decorators below

def keyword( *args, **kwargs ):
	return _register( *args, **(kwargs | { '_current_frame': currentframe(), '_class': Keyword } ) )

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

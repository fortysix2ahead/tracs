
from __future__ import annotations

from enum import Enum
from importlib import import_module
from inspect import currentframe, FrameInfo, getmembers, isclass, signature as getsignature
from logging import getLogger
from pkgutil import extend_path, iter_modules
from re import compile
from types import ModuleType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from attrs import define, field
from fs.osfs import OSFS

from tracs.core import Keyword

log = getLogger( __name__ )

DECORATOR_TYPE = compile( r'^_[a-z]+$' )

@define
class Decorator:

	class Init( Enum ):
		none = 0,
		cls = 1,
		inst = 2,
		fn = 3,
		call = 4

	fncls: Callable|Type = field( default=None )
	args: Tuple = field( factory=tuple )
	kwargs: Dict = field( factory=dict )
	frame = field( default=None )

	cls: Type = field( default=None )
	init: Init = field( default=Init.call )

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

	_importer: Dict[str, Keyword] = field( factory=dict, alias='_importer' )
	_keyword: Dict[str, Keyword] = field( factory=dict, alias='_keyword' )
	_normalizer: Dict[str, Keyword] = field( factory=dict, alias='_normalizer' )
	_resourcetype: Dict[str, Keyword] = field( factory=dict, alias='_resourcetype' )
	_service: Dict[str, Keyword] = field( factory=dict, alias='_service' )
	_setup: Dict[str, Keyword] = field( factory=dict, alias='_setup' )
	_virtualfield: Dict[str, Keyword] = field( factory=dict, alias='_virtualfield' )

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
		decorator_types = [ att[1:] for att in dir( Registry ) if DECORATOR_TYPE.fullmatch( att ) ]
		for decorator_type in decorator_types:
			for d in filter( lambda dec:  dec.type == decorator_type, cls.decorators ):
				try:
					match d.init:
						case Decorator.Init.call:
							getattr( cls._registry, f'_{d.type}' )[d.name] = (inst := d())
							log.debug( f'registered {inst} provided by decorated function/class {d.fncls}' )
						case Decorator.Init.cls:
							getattr( cls._registry, f'_{d.type}' )[d.name] = d.fncls
							log.debug( f'registered {d.type} class {d.fncls}' )
						case Decorator.Init.fn:
							getattr( cls._registry, f'_{d.type}' )[d.name] = d.fncls
							log.debug( f'registered {d.type} function {d.fncls}' )
						case _:
							log.warning( f'unknown descriptor type {d.type}' ) # should not happen

				except (AttributeError, TypeError): # need to be extended
					log.error( f'error calling decorated object {d.fncls}' )

		return cls._registry

	@staticmethod
	def register_decorator(
			fncls: Callable | Type,
			args: Tuple, kwargs: Dict,
			frame: FrameInfo = None,
			cls: Type = None,
			init: Decorator.Init = Decorator.Init.call
	) -> Decorator:
		PluginManager.decorators.append( d := Decorator( fncls, args, kwargs, frame, cls, init ) )
		log.debug( f'registered decorator [green]{d.name}[/green] from {d.fncls} in module [green]{d.module}[/green]' )
		return d

# decorators

def _register( *args, **kwargs ) -> Callable:
	_class = kwargs.pop( '_class', None )
	_frame = kwargs.pop( '_frame', None )
	_init = kwargs.pop( '_init', Decorator.Init.none )

	def _inner( fncls ):
		if fncls is not None:
			PluginManager.register_decorator( fncls, args, kwargs, _frame, _class, _init )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		PluginManager.register_decorator( args[0], (), {}, _frame, _class, _init )
		if isclass( args[0] ):
			return args[0]

	return _inner

# actual real-world decorators below

def keyword( *args, **kwargs ):
	return _register( *args, **(kwargs | { '_frame': currentframe(), '_init': Decorator.Init.call } ) )

def normalizer( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.call } ) )

def virtualfield( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.call } ) )

def importer( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def resourcetype( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def service( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def setup( *args, **kwargs ):
	return _register( *args, **(kwargs | { '_frame': currentframe(), '_init': Decorator.Init.fn } ) )

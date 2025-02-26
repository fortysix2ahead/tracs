
from __future__ import annotations

from enum import Enum
from importlib import import_module
from inspect import currentframe, FrameInfo, getmembers, isclass, signature as getsignature
from logging import getLogger
from pkgutil import extend_path, iter_modules
from re import compile, match
from types import ModuleType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type

from attrs import define, field
from fs.osfs import OSFS

from tracs.constants import PLUGINS_PKG, PLUGIN_PATH
from tracs.core import Keyword, Normalizer
from tracs.protocols import Importer, VirtualField
from tracs.resources import ResourceType
from tracs.service import Service, ServiceManager

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

	# important: the names of the fields match the names of the decorators below + an underscore
	_importer: Dict[str, Importer] = field( factory=dict, alias='_importer' )
	_keyword: Dict[str, Keyword] = field( factory=dict, alias='_keyword' )
	_normalizer: Dict[str, Normalizer] = field( factory=dict, alias='_normalizer' )
	_resourcetype: Dict[str, ResourceType] = field( factory=dict, alias='_resourcetype' )
	_service: Dict[str, Type[Service]] = field( factory=dict, alias='_service' )
	_setup: Dict[str, Callable] = field( factory=dict, alias='_setup' )
	_virtualfield: Dict[str, VirtualField] = field( factory=dict, alias='_virtualfield' )

	@classmethod
	def decorator_fields( cls ) -> List[str]:
		return [ att for att in dir( cls ) if DECORATOR_TYPE.fullmatch( att ) ]

	def is_initialized( self ) -> bool:
		return any( [ len( getattr( self, att ) ) > 1 for att in self.__class__.decorator_fields() ] )

	@property
	def importers( self ) -> List[Importer]:
		return list( self._importer.values() )

	@property
	def keywords( self ) -> List[Keyword]:
		return list( self._keyword.values() )

	@property
	def normalizers( self ) -> List[Normalizer]:
		return list( self._normalizer.values() )

	def resource_types( self ) -> List[ResourceType]:
		return list( self._resourcetype.values() )

	def resource_type_for_extension( self, extension: str ) -> Optional[ResourceType]:
		return next( (rt for rt in self.resource_types() if rt.extension() == extension), None )

	def resource_type_for_suffix( self, suffix: str ) -> Optional[ResourceType]:
		# first round: prefer suffix in special part of type: 'gpx' matches 'application/xml+gpx'
		for key, rt in self._resourcetype.items():
			if m := match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				return rt

		# second round: suffix after slash: 'gpx' matches 'application/gpx'
		for key, rt in self._resourcetype.items():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ):
				return rt

		return None

	def summary_types( self ) -> List[ResourceType]:
		return [ rt for rt in self._resourcetype.values() if rt.summary ]

	def summary_type_names( self ) -> List[str]:
		return [ rt.name for rt in self.summary_types() ]

	def recording_types( self ) -> List[ResourceType]:
		return [rt for rt in self._resourcetype.values() if rt.recording]

	def recording_type_names( self ) -> List[str]:
		return [rt.name for rt in self.recording_types()]

	@property
	def services( self ) -> List[Type[Service]]:
		return [s for s in self._service.values()]

	@property
	def setups( self ) -> List[Callable]:
		return [s for s in self._setup.values()]

	@property
	def virtual_fields( self ) -> List[VirtualField]:
		return [ vf for vf in self._virtualfield.values() ]

@define
class PluginManager:

	_instance: ClassVar[PluginManager] = None

	_modules: Dict[str, ModuleType] = field( factory=dict, alias='_modules' )
	_decorators: List[Decorator] = field( factory=list, alias='_decorators' )
	_registry: Registry = field( factory=Registry, alias='_registry' )
	_service_mgr: ServiceManager = field( factory=ServiceManager, alias='_service_mgr' )

	_plugin_paths: List[str] = field( factory=list, alias='_plugin_paths' )

	@classmethod
	def inst( cls ) -> PluginManager:
		if not PluginManager._instance:
			PluginManager._instance = PluginManager()
		return PluginManager._instance

	def init( self, plugin_paths: Optional[List[str]], reinit: bool = False ) -> PluginManager:
		self._plugin_paths = plugin_paths or []

		# this is just for debug/dev purposes
		if reinit:
			log.debug( f'clearing plugin manager content' )
			self._modules.clear()
			self._decorators.clear()

		# noinspection PyUnresolvedReferences
		import tracs.plugins

		# extend plugin path and load additional, non-optional plugins
		for pp in plugin_paths or []:
			plugin_path = OSFS( root_path=pp, expand_vars=True ).getsyspath( PLUGIN_PATH )
			tracs.plugins.__path__ = extend_path( [plugin_path], PLUGINS_PKG )
			log.debug( f'adding {plugin_path} to list of plugin search paths' )

		# load plugin modules
		for finder, name, ispkg in iter_modules( tracs.plugins.__path__ ):
			try:
				self._modules[name] = import_module( f'tracs.plugins.{name}' )
			except ImportError:
				log.error( f'failed to import module tracs.plugins.{name}', exc_info=True )
				continue

		return self # for convenience

	def registry( self ) -> Registry:
		if not self._registry.is_initialized():
			log.debug( 'registry is not initialized, evaluating decorators ...' )
			decorator_types = [ f[1:] for f in Registry.decorator_fields() ]
			for decorator_type in decorator_types:
				for d in filter( lambda dec: dec.type == decorator_type, self._decorators ):
					try:
						match d.init:
							case Decorator.Init.call:
								if isinstance( inst := d(), list ):
									for i in inst:
										# todo: improve as we rely on i having a name attribute -> what to do if not?
										getattr( self._registry, f'_{d.type}' )[i.name] = i
										log.debug( f'registered {i} provided by decorated function/class {d.fncls}' )
								else:
									getattr( self._registry, f'_{d.type}' )[d.name] = inst
									log.debug( f'registered {inst} provided by decorated function/class {d.fncls}' )
							case Decorator.Init.cls:
								getattr( self._registry, f'_{d.type}' )[d.name] = d.fncls
								log.debug( f'registered {d.type} class {d.fncls}' )
							case Decorator.Init.fn:
								getattr( self._registry, f'_{d.type}' )[d.name] = d.fncls
								log.debug( f'registered {d.type} function {d.fncls}' )
							case _:
								log.warning( f'unknown descriptor type {d.type}' ) # should not happen

					except (AttributeError, TypeError): # need to be extended
						log.error( f'error calling decorated object {d.fncls}', exc_info=True )

		else:
			log.debug( 'skipping registry initialization, decorators have already been evaluated' )

		return self._registry

	@property
	def plugins( self ) -> List[ModuleType]:
		return list( self._modules.values() )

	@property
	def service_mgr( self ) -> ServiceManager:
		return self._service_mgr

	@staticmethod
	def register_decorator(
			fncls: Callable | Type,
			args: Tuple, kwargs: Dict,
			frame: FrameInfo = None,
			cls: Type = None,
			init: Decorator.Init = Decorator.Init.call
	) -> Decorator:
		PluginManager.inst()._decorators.append( d := Decorator( fncls, args, kwargs, frame, cls, init ) )
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
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.call } ) )

def service( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def setup( *args, **kwargs ):
	return _register( *args, **(kwargs | { '_frame': currentframe(), '_init': Decorator.Init.fn } ) )

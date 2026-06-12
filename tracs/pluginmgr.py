
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
from more_itertools.recipes import first_true

from tracs.constants import PLUGINS_PKG, PLUGIN_PATH
from tracs.core import DerivedField, Keyword, Normalizer
from tracs.protocols import Importer, VirtualField
from tracs.resources import ResourceType
from tracs.service import Service
from tracs.servicemgr import ServiceManager

log = getLogger( __name__ )

DECORATOR_TYPE = compile( r'^_[a-z]+$' )
FACTORY_PLUGINS = [
	'json', 'xml', 'gpx', 'tcx', 'keywords', 'normalizers', 'image', 'fields', 'csv', 'bikecitizens', 'local', 'polar', 'strava', 'waze'
]

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

	_decorators: List[Decorator] = field( factory=list, alias='decorators' )
	_decorated_objs: Dict[str, Dict] = field( factory=dict, alias='_decorated_objs' )

	def __attrs_post_init__( self ):
		for d in self._decorators:
			match d.type:
				case 'derived_field':
					df = DerivedField( **d.kwargs, fn=d.fncls )
					df.name = d.name or df.name
					self._ddict( d.type )[d.name] = df
				case 'importer':
#					self._ddict( 'importer' )[d.name] = d.fncls( **d.kwargs ) # todo
					self._ddict( d.type )[d.name] = d.fncls()
				case 'keyword':
					self._ddict( d.type )[d.name] = d.fncls()
				case 'normalizer':
					self._ddict( d.type )[d.name] = d.fncls()
				case 'resourcetype':
					_type = d.fncls()
					if isinstance( _type := d.fncls(), list ):
						for t in _type:
							self._ddict( d.type )[t.name] = t
					else:
						self._ddict( d.type )[_type.name] = _type
				case 'service':
					self._ddict( d.type )[d.name] = d.fncls
				case 'setup':
					self._ddict( d.type )[d.name] = d.fncls
				case 'virtualfield':
					self._ddict( d.type )[d.name] = d.fncls()
				case _:
					pass

	def is_initialized( self ) -> bool:
		return any( [ len( d ) > 1 for d in self._decorated_objs.values() ] )

	def _ddict( self, type: str ) -> Dict[str, Any]:
		if not self._decorated_objs.get( type ):
			self._decorated_objs[type] = dict()
		return self._decorated_objs[type]

	def register( self, name: str, type: str, fncls: Any ) -> None:
		self._ddict( type=type )[name] = fncls

	# importer

	@property
	def importers( self ) -> List[Importer]:
		return list( self._ddict( 'importer' ).values() )

	def importer( self, type: str ) -> Optional[Importer]:
		return first_true( self.importers(), lambda i: i.type == type )

	# keywords

	@property
	def keywords( self ) -> List[Keyword]:
		return list( self._ddict( 'keyword' ).values() )

	# normalizers

	@property
	def normalizers( self ) -> List[Normalizer]:
		return list( self._ddict( 'normalizer' ).values() )

	# resource types

	def resource_types( self ) -> List[ResourceType]:
		return list( self._ddict( 'resourcetype' ).values() )

	def resource_type( self, name: str ) -> Optional[ResourceType]:
		return first_true( self.resource_types(), pred=lambda rt: rt.name == name )

	def resource_type_for_extension( self, extension: str ) -> Optional[ResourceType]:
		return next( (rt for rt in self.resource_types() if rt.extension() == extension), None )

	def resource_type_for_suffix( self, suffix: str ) -> Optional[ResourceType]:
		# first round: prefer suffix in special part of type: 'gpx' matches 'application/xml+gpx'
		for key, rt in self.resource_types():
			if m := match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				return rt

		# second round: suffix after slash: 'gpx' matches 'application/gpx'
		for key, rt in self.resource_types():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ):
				return rt

		return None

	def summary_types( self ) -> List[ResourceType]:
		return [ rt for rt in self.resource_types() if rt.summary ]

	def summary_type_names( self ) -> List[str]:
		return [ rt.name for rt in self.summary_types() ]

	def recording_types( self ) -> List[ResourceType]:
		return [rt for rt in self.resource_types() if rt.recording]

	def recording_type_names( self ) -> List[str]:
		return [rt.name for rt in self.recording_types()]

	# services

	@property
	def services( self ) -> List[Type[Service]]:
		return [s for s in self._ddict( 'service' ).values()]

	# setup functions

	@property
	def setups( self ) -> List[Callable]:
		return [s for s in self._ddict( 'setup' ).values()]

	# derived fields

	@property
	def derived_fields( self ) -> List[DerivedField]:
		return [ df for df in self._ddict( 'derived_field' ).values() ]

	@property
	def virtual_fields( self ) -> List[VirtualField]:
		return [ vf for vf in self._ddict( 'virtualfield' ).values() ]

@define
class PluginManager:

	_instance: ClassVar[PluginManager|None] = None

	plugin_paths: List[str] = field( factory=list )
	plugin_modules: List[str] = field( factory=list )
	autoload: bool = field( default=False )

	_modules: Dict[str, ModuleType] = field( factory=dict, alias='_modules' )
	_decorators: List[Decorator] = field( factory=list, alias='_decorators' )
	_registry: Registry = field( default=None, alias='_registry' )
	_service_mgr: ServiceManager = field( factory=ServiceManager, alias='_service_mgr' )

	@staticmethod
	def instance( *args, **kwargs ) -> PluginManager|None:
		if not PluginManager._instance:
			PluginManager._instance = PluginManager( *args, **kwargs )
		return PluginManager._instance

	def _load_modules( self, modules: List[str]|None ):
		for m in modules or []:
			try:
				log.debug( f'attempting to load plugin module tracs.plugins.{m} ...' )
				self._modules[m] = import_module( f'tracs.plugins.{m}' )
			except ImportError:
				log.error( f'failed to import module tracs.plugins.{m}', exc_info=True )

	def init( self, plugin_paths: List[str]|None, plugin_names: List[str]|None ):
		log.debug( f'loading factory plugins ...' )
		self._load_modules( FACTORY_PLUGINS )

		log.debug( f'loading user-defined plugins ...' )
		if plugin_paths and plugin_names:
			self.plugin_paths, self.plugin_modules = plugin_paths, plugin_names
			self._load_extensions( self.plugin_paths, self.plugin_modules, False )

		log.debug( f'initializing extension registry ...' )
		self._init_registry()

		log.debug( f'initializing service manager ...' )
		self._init_service_manager()

	def _load_extensions( self, plugin_paths: List[str]|None, plugin_names: List[str]|None, autoload: bool = False ) -> None:
		# noinspection PyUnresolvedReferences
		import tracs.plugins

		autoload = False  # autoload plugin modules, this is currently disabled

		# extend plugin path to load additional plugins
		for p in plugin_paths or []:
			plugin_path = OSFS( root_path=p, expand_vars=True ).getsyspath( PLUGIN_PATH )
			tracs.plugins.__path__ = extend_path( [plugin_path], PLUGINS_PKG )
			log.debug( f'adding {plugin_path} to list of plugin search paths' )

		if autoload:
			for finder, name, ispkg in iter_modules( tracs.plugins.__path__ ):
				try:
					self._modules[name] = import_module( f'tracs.plugins.{name}' )
				except ImportError:
					log.error( f'failed to import module tracs.plugins.{name}', exc_info=True )
					continue

		else:
			self._load_modules( plugin_names )

	def _init_registry( self ):
		self._registry = Registry( self._decorators )

	def _init_service_manager( self ):
		self._service_mgr = ServiceManager()

	def reinit( self ):
		# only for development
		log.debug( f'clearing plugin manager content' )
		self._modules.clear()
		self._decorators.clear()

	def registry_( self ) -> Registry:
		if not self._registry.is_initialized():
			log.debug( f'registry is not yet initialized, evaluating {len( self._decorators )} decorators' )

			for d in self._decorators:
				match d.init:
					case Decorator.Init.call:
						if isinstance( inst := d(), list ):
							for i in inst:
								# todo: improve as we rely on i having a name attribute -> what to do if not?
								# getattr( self._registry, f'_{d.type}' )[i.name] = i
								self._registry.register( d.name, d.type, i )
								log.debug( f'registered {i} provided by decorated function/class {d.fncls}' )

						else:
							self._registry.register( d.name, d.type, inst )
							log.debug( f'registered {inst} provided by decorated function/class {d.fncls}' )

					case Decorator.Init.inst:
						pass # todo: case not yet supported

					case Decorator.Init.cls:
						self._registry.register( d.name, d.type, d.fncls )
						log.debug( f'registered {d.type} class {d.fncls}' )

					case Decorator.Init.fn:
						self._registry.register( d.name, d.type, d.fncls )
						log.debug( f'registered {d.type} function {d.fncls}' )

					case _:
						log.warning( f'unknown descriptor type {d.type}' )  # should not happen

		else:
			log.debug( 'skipping registry initialization, decorators have already been evaluated' )

		return self._registry

	@property
	def registry( self ) -> Registry:
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
		PluginManager.instance()._decorators.append( d := Decorator( fncls, args, kwargs, frame, cls, init ) )
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
		PluginManager.instance().register_decorator( args[0], (), {}, _frame, _class, _init )
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

def derived_field( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.fn } ) )

def importer( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def resourcetype( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.call } ) )

def service( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_frame': currentframe(), '_init': Decorator.Init.cls } ) )

def setup( *args, **kwargs ):
	return _register( *args, **(kwargs | { '_frame': currentframe(), '_init': Decorator.Init.fn } ) )

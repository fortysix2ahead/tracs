
from __future__ import annotations

from importlib import import_module
from inspect import getmembers, isclass, signature as getsignature
from logging import getLogger
from pkgutil import extend_path, iter_modules
from types import ModuleType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from fs.osfs import OSFS

log = getLogger( __name__ )

factory_plugins = [ 'csv', 'json', 'xml', 'gpx', 'tcx' ]

class PluginManager:

	plugins: ClassVar[Dict[str, ModuleType]] = {}

	importers: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	keywords: ClassVar[List[Tuple]] = []
	normalizers: ClassVar[List[Tuple]] = []
	resource_types: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	services: ClassVar[List[Tuple[Type, Tuple, Dict]]] = []
	setups: ClassVar[List[Tuple]] = []
	virtual_fields: ClassVar[List[Tuple]] = []

	@classmethod
	def init( cls, plugin_paths: Optional[List[str]] = None ):
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
	_fncls_list = kwargs.pop( '__fncls_list__' )
	_decorator_name = kwargs.pop( '__decorator_name__' )

	def _inner( fncls ):
		# def _wrapper( *wrapper_args, **wrapper_kwargs ):
		#	fn( *wrapper_args, **wrapper_kwargs )

		if fncls is not None:
			_fncls_list.append( (fncls, args, kwargs) )
			log.debug( f'registered {_decorator_name} function/class from {fncls} in module {_fnspec( fncls )[1]}' )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		_fncls_list.append( (args[0], (), {}) )
		log.debug( f'registered {_decorator_name} function from {args[0]} in module {_fnspec( args[0] )[1]}' )

		if isclass( args[0] ):
			return args[0]

	return _inner

# actual real-world decorators below

def keyword( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.keywords, __decorator_name__='keyword' )

def normalizer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.normalizers, __decorator_name__='normalizer' )

def virtualfield( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.virtual_fields, __decorator_name__='virtualfield' )

def importer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.importers, __decorator_name__='importer' )

def resourcetype( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.resource_types, __decorator_name__='resourcetype' )

def service( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.services, __decorator_name__='service' )

def setup( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = PluginManager.setups, __decorator_name__='setup' )

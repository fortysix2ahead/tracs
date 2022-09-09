
from __future__ import annotations

# from inspect import getfullargspec
from inspect import getmembers
from inspect import isclass
from importlib import import_module
from logging import getLogger
from pkgutil import walk_packages
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union
from typing import cast

from ..base import Handler
from ..base import Importer
from ..base import Service
from ..config import KEY_CLASSIFER

log = getLogger( __name__ )
NS_PLUGINS = __name__

class Registry:

	classifier: str = KEY_CLASSIFER
	document_classes: Dict[str, Type] = {}
	downloaders = {}
	fetchers = {}
	handlers: Dict[str, List[Handler]] = {}
	importers: Dict[str, List[Importer]] = {}
	services: Dict[str, Service] = {}
	service_classes: Dict[str, Type] = {}

	# handlers

	@classmethod
	def handler_for( cls, type: str ) -> Optional[Handler]:
		handler_list = Registry.handlers.get( type ) or []
		return handler_list[0] if len( handler_list ) > 0 else None

	@classmethod
	def handlers_for( cls, type: str ):
		return Registry.handlers.get( type ) or []

	@classmethod
	def register_handler( cls, handler: Handler, type: str ):
		handler_list = Registry.handlers.get( type ) or []
		if handler not in handler_list:
			handler_list.append( handler )
			Registry.handlers[type] = handler_list
			log.debug( f'registered handler {handler.__class__} for type {type}' )

	# importers

	@classmethod
	def importer_for( cls, type: str ) -> Optional[Importer]:
		importer_list = Registry.importers.get( type ) or []
		return importer_list[0] if len( importer_list ) > 0 else None

	@classmethod
	def importers_for( cls, type: str ):
		return Registry.importers.get( type ) or []

	@classmethod
	def register_importer( cls, importer: Importer, type: str ):
		importer_list = Registry.importers.get( type ) or []
		if importer not in importer_list:
			importer_list.append( importer )
			Registry.importers[type] = importer_list
			log.debug( f'registered importer {importer.__class__} for type {type}' )

	@classmethod
	def register_functions( cls, functions: Dict[Union[str, Tuple[str, str]], Callable], dictionary: Dict ) -> None:
		for item_key, item_value in functions.items():
			dictionary[item_key] = item_value

	@classmethod
	def register_function( cls, key: str or Tuple[str, str], fn: Callable, dictionary: Mapping ) -> Callable:
		if not key or not fn:
			log.warning( 'unable to register function with an empty key and/or function' )
		else:
			if type( key ) is tuple and key[0] is None: # allow (None, 'field') as key and treat it as 'field'
				key = key[1]
			dictionary[key] = fn

		return fn

	@classmethod
	def unregister_function( cls, key: str or Tuple[str, str], dictionary: Dict ) -> None:
		del dictionary[key]

	@classmethod
	def function_for( cls, key: str or Tuple[str, str], dictionary: Mapping ) -> Optional[Callable]:
		return dictionary.get( key )

	@classmethod
	def functions_for( cls, key: Optional[str], dictionary: Mapping ) -> Dict[str, Callable]:
		rval = {}
		for item_key, item_fn in dictionary.items():
			if key and type( item_key ) is tuple and key == item_key[0]:
				rval[item_key[1]] = item_fn
			elif not key and type( item_key ) is str:
				rval[item_key] = item_fn
		return rval

# internal helpers

def _spec( func: Callable ) -> Tuple[str, str]:
	"""
	Helper for examining a provided function. Returns the module name and the name of the function as a tuple.
	The module only contains the name of the module alone, not the fully qualified name.

	:param func: function to be examined
	:return: module + name as a tuple
	"""
	name = None
	module = None
	#members = getmembers( func )
	for k, v in getmembers( func ):
		if k == '__name__':
			name = v
		elif k == '__module__':
			module = v.rsplit( '.', 1 )[1]

	#print( getfullargspec( fn ) )

	return module, name

# decorators

def _register( args, kwargs, dictionary, callable_fn = False ) -> Union[Type, Callable]:
	"""
	Helper for registering mappings returned from the provided decorated function to the provided dictionary.

	:param args:
	:param kwargs:
	:param dictionary:
	:param callable_fn:
	:return: returns the provided callable (as convenience for callers)
	"""
	def decorated_fn( fn ):
		dec_ns, dec_name = _spec( fn )
		if callable_fn:
			dec_call_result = fn()
			for dec_fn_name, dec_fn_value in dec_call_result.items():
				if kwargs['classifier']:
					Registry.register_function( (kwargs['classifier'], dec_fn_name), dec_fn_value, dictionary )
				else:
					Registry.register_function( dec_fn_name, dec_fn_value, dictionary )
		else:
			if kwargs['classifier']:
				Registry.register_function( (kwargs['classifier'], dec_name), fn, dictionary )
			else:
				Registry.register_function( dec_name, fn, dictionary )

		return fn

	# call via standard decorator, no namespace argument is provided, namespace is taken from module containing the function
	if len( args ) == 1:
		ns, name = _spec( args[0] )
		if callable_fn:
			call_result = args[0]()
			for fn_name, fn_value in call_result.items():
				Registry.register_function( (ns, fn_name), fn_value, dictionary )
		else:
			Registry.register_function( (ns, name), args[0], dictionary )
		return args[0]
	# call via decorator with arguments, namespace argument is provided
	elif len( args ) == 0 and 'classifier' in kwargs:
		return decorated_fn
	else:
		raise RuntimeError( 'unable to register function -> this needs to be reported' )

# decorator for service classes

def service( cls: Type ):
	if isclass( cls ):
		module, name = _spec( cls )
		Registry.service_classes[module] = cls
		# config, state = plugin_config_state( module ) # todo: this does not work as expected, but we'll leave it in for now
		# Registry.services[module] = cls( config=config, state=state )
		Registry.services[module] = cls()
		log.debug( f'registered service class {cls}' )
		return cls
	else:
		raise RuntimeError( 'only classes can be used with the @service decorator' )

# experimental decorators

# A decorator with arguments is defined as a function that returns a standard decorator.
# A standard decorator is defined as function that returns a function.
def document( *args, **kwargs ):
	def document_class( cls ):
		if isclass( cls ):
			# module_kwarg, name_kwarg = _spec( cls )
			Registry.document_classes[kwargs['namespace']] = cls
			log.debug( f"registered document class {cls} with namespace {kwargs['namespace']}" )
			return cls
		else:
			raise RuntimeError( 'only classes can be used with the @document decorator' )

	if len( args ) == 0 and 'namespace' in kwargs:
		return document_class
	elif len( args ) == 1 and isclass( args[0] ):
		module_arg, name_arg = _spec( args[0] )
		Registry.document_classes[module_arg] = args[0]
		log.debug( f'registered document class {args[0]} with namespace {module_arg}' )
		return args[0]
	else:
		raise RuntimeError( 'only classes can be used with the @document decorator' )

def handler( *args, **kwargs ):
	def handler_class( cls ):
		if isclass( cls ):
			instance = cast( Handler, cls() )
			for t in instance.types():
				Registry.register_handler( instance, t )
			return cls
		else:
			raise RuntimeError( 'only classes can be decorated with the @handler decorator' )

	if len( args ) == 0 and 'types' in kwargs:
		return handler_class
	elif len( args ) == 1:
		handler_class( args[0] )

def importer( *args, **kwargs ):
	def importer_class( cls ):
		if isclass( cls ):
			instance = cast( Importer, cls() )
			for t in kwargs['types']:
				Registry.register_importer( instance, t )
			return cls
		else:
			raise RuntimeError( 'only classes can be decorated with the @handler decorator' )

	if len( args ) == 0 and 'types' in kwargs:
		return importer_class
	elif len( args ) == 1:
		importer_class( args[0] )

def fetch( fn ):
	return Registry.register_function( _spec( fn ), fn, Registry.fetchers )

def download( fn ):
	return Registry.register_function( _spec( fn ), fn, Registry.downloaders )

# setup

def load( plugin_pkgs: List[str] = None, disabled: List[str] = None ):
	plugin_pkgs = plugin_pkgs if plugin_pkgs else [NS_PLUGINS]
	disabled = disabled if disabled else []

	for plugin_pkg in plugin_pkgs:
		log.debug( f'attempting to load plugins from namespace {plugin_pkg}' )

		plugins_module = import_module( plugin_pkg )
		for finder, name, ispkg in walk_packages( plugins_module.__path__ ):
			if name not in disabled:
				qname = f'{plugin_pkg}.{name}'
				plugin = import_module( qname )
				log.debug( f'imported plugin {plugin}' )
			else:
				log.debug( f'skipping import of disabled plugin {name} in package {plugin_pkg}' )

# trigger auto load

load()

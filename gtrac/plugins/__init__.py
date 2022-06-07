
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

from ..base import Service
from ..config import KEY_CLASSIFER
from ..config import plugin_config_state

log = getLogger( __name__ )
NS_PLUGINS = __name__

class Registry:

	accessors: Dict[str or Tuple[str, str], Callable ] = {}
	classifier: str = KEY_CLASSIFER
	document_classes: Dict[str, Type] = {}
	downloaders = {}
	fetchers = {}
	services: Dict[str, Service] = {}
	service_classes: Dict[str, Type] = {}
	transformers: Dict[str or Tuple[str, str], Callable ] = {}
	writers: Dict[str or Tuple[str, str], Callable ] = {}

	@classmethod
	def register_accessor( cls, key: str or Tuple[str, str], fn: Callable ) -> None:
		cls.register_function( key, fn, cls.accessors )

	@classmethod
	def register_accessors( cls, classifier: Optional[str], fns: Dict[str, Callable] ):
		for key, fn in fns.items(): cls.register_function( (classifier, key), fn, cls.accessors )

	@classmethod
	def register_transformer( cls, key: str or Tuple[str, str], fn: Callable ) -> None:
		cls.register_function( key, fn, cls.transformers )

	@classmethod
	def register_transformers( cls, classifier: Optional[str], fns: Dict[str, Callable] ):
		for key, fn in fns.items(): cls.register_function( (classifier, key), fn, cls.transformers )

	@classmethod
	def register_writer( cls, key: str or Tuple[str, str], fn: Callable ) -> None:
		cls.register_function( key, fn, cls.writers )

	@classmethod
	def register_writers( cls, classifier: Optional[str], fns: Dict[str, Callable] ):
		for key, fn in fns.items(): cls.register_function( (classifier, key), fn, cls.writers )

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

			# for logging/debugging only
			dict_name = None
			if dictionary is Registry.accessors:
				dict_name = 'accessor'
			elif dictionary is Registry.transformers:
				dict_name = 'transformer'
			elif dictionary is Registry.writers:
				dict_name = 'writer'

			log.debug( f'registered {dict_name} function {fn} for {key}' )

		return fn

	@classmethod
	def unregister_accessor( cls, key: str or Tuple[str, str] ) -> None:
		cls.unregister_function( key, cls.accessors )

	@classmethod
	def unregister_transformer( cls, key: str or Tuple[str, str] ) -> None:
		cls.unregister_function( key, cls.transformers )

	@classmethod
	def unregister_writer( cls, key: str or Tuple[str, str] ) -> None:
		cls.unregister_function( key, cls.writers )

	@classmethod
	def unregister_all( cls ) -> None:
		cls.accessors.clear()
		cls.transformers.clear()
		cls.writers.clear()

	@classmethod
	def unregister_function( cls, key: str or Tuple[str, str], dictionary: Dict ) -> None:
		del dictionary[key]

	@classmethod
	def accessor( cls, key: str or Tuple[str, str] ) -> Optional[Callable]:
		return cls.function_for( key, Registry.accessors )

	@classmethod
	def transformer( cls, key: str or Tuple[str, str] ) -> Optional[Callable]:
		return cls.function_for( key, Registry.transformers )

	@classmethod
	def writer( cls, key: str or Tuple[str, str] ) -> Optional[Callable]:
		return cls.function_for( key, Registry.writers )

	@classmethod
	def function_for( cls, key: str or Tuple[str, str], dictionary: Mapping ) -> Optional[Callable]:
		return dictionary.get( key )

	@classmethod
	def accessors_for( cls, key: Optional[str] ) -> Dict[str, Callable]:
		return cls.functions_for( key, Registry.accessors )

	@classmethod
	def transformers_for( cls, key: Optional[str] ) -> Dict[str, Callable]:
		return cls.functions_for( key, Registry.transformers )

	@classmethod
	def writers_for( cls, key: Optional[str] ) -> Dict[str, Callable]:
		return cls.functions_for( key, Registry.writers )

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

def accessor( *args, **kwargs ):
	return _register( args, kwargs, Registry.accessors )

def accessors( *args, **kwargs ):
	return _register( args, kwargs, Registry.accessors, True )

def transformer( *args, **kwargs ):
	return _register( args, kwargs, Registry.transformers )

def transformers( *args, **kwargs ):
	return _register( args, kwargs, Registry.transformers, True )

def writer( *args, **kwargs ):
	return _register( args, kwargs, Registry.writers )

def writers( *args, **kwargs ):
	return _register( args, kwargs, Registry.writers, True )

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
		config, state = plugin_config_state( module ) # todo: this does not work as expected, but we'll leave it in for now
		Registry.services[module] = cls( config=config, state=state )
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


from __future__ import annotations

from dataclasses import Field, fields
from enum import Enum
from importlib import import_module
from inspect import getmembers, isclass, isfunction
from logging import getLogger
from pathlib import Path
from pkgutil import walk_packages
from re import match
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Type, Union

from confuse import NotFoundError
from dataclass_factory import Factory, Schema

from tracs.activity import Activity
from tracs.config import ApplicationContext, KEY_CLASSIFER
from tracs.core import Keyword, Normalizer, vfield, VirtualField, VirtualFields
from tracs.protocols import Handler, Importer, Service
from tracs.resources import ResourceType
from tracs.uid import UID

log = getLogger( __name__ )

NS_PLUGINS = 'tracs.plugins'
_ARGS, _KWARGS = (), {} # helpers ...

class EventTypes( Enum ):

	plugin_loaded = 'plugin_loaded'
	resource_loaded = 'resource_loaded'
	rule_normalizer_registered = 'rule_normalizer_registered'
	service_created = 'service_created'
	virtual_field_registered = 'virtual_field_registered'

class Registry:

	activity_field_resolvers = {}
	classifier: str = KEY_CLASSIFER
	ctx: ApplicationContext = None
	dataclass_factory = Factory( debug_path=True, schemas={} )
	document_classes: Dict[str, Type] = {}
	document_types: Dict[str, Type] = {}
	event_listeners = {}
	handlers: Dict[str, List[Handler]] = {}
	importers: Dict[str, List[Importer]] = {}
	resource_types: Dict[str, ResourceType] = {}
	rule_keywords: Dict[str, Keyword] = {}
	rule_normalizers: Dict[str, Normalizer] = {}
	setup_functions: Dict[str, Callable] = {}
	services: Dict[str, Service] = {}
	service_classes: Dict[str, Type] = {}
	virtual_fields: Dict[str, VirtualField] = {}

	# register virtual_fields dict with activity
	VirtualFields.__fields__ = virtual_fields

	@classmethod
	def instantiate_services( cls, ctx: Optional[ApplicationContext] = None, **kwargs ):
		_ctx = ctx if ctx else Registry.ctx
		for name, service_type in Registry.service_classes.items():
			service_base_path = Path( _ctx.db_dir_path, name )
			service_overlay_path = Path( _ctx.db_overlay_path, name )

			# find config/state values
			service_cfg = ctx.plugin_config( name )
			service_state = ctx.plugin_state( name )

			if service_cfg.get( 'enabled', True ):
				Registry.services[name] = service_type( ctx=ctx, **{ **kwargs, **service_cfg, **service_state, **{ 'base_path': service_base_path, 'overlay_path': service_overlay_path } } )
				# log.debug( f'created service instance {name}, with base path {service_base_path}' )
				Registry.notify( EventTypes.service_created, Registry.services[name] )
			else:
				log.debug( f'skipping instance creation for disabled plugin {name}' )

	# resource types

	@classmethod
	def register_resource_type( cls, resource_type ) -> None:
		Registry.resource_types[resource_type.type] = resource_type

	# noinspection PyUnresolvedReferences
	@classmethod
	def resource_type_for_extension( cls, extension: str ) -> Optional[ResourceType]:
		return next( (rt for rt in Registry.resource_types.values() if rt.extension() == extension), None )

	@classmethod
	def resource_type_for_suffix( cls, suffix: str ) -> Optional[str]:
		# first round: prefer suffix in special part of type: 'gpx' matches 'application/xml+gpx'
		for key in Registry.importers.keys():
			if m := match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				return key

		# second round: suffix after slash: 'gpx' matches 'application/gpx'
		for key in Registry.importers.keys():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ):
				return key

		return None

	# rules and normalizing

	@classmethod
	def register_keyword( cls, keyword: Keyword ):
		cls.rule_keywords[keyword.name] = keyword
		log.debug( f'registered rule keyword "{keyword.name}"' )

	@classmethod
	def register_keywords( cls, *keywords: Keyword ):
		[ cls.register_keyword( k ) for k in keywords ]

	@classmethod
	def register_normalizer( cls, *normalizer: Normalizer ) -> None:
		for n in normalizer:
			cls.rule_normalizers[n.name] = n
			cls.notify( EventTypes.rule_normalizer_registered, field=n )

	@classmethod
	def rule_normalizer_type( cls, name: str ) -> Any:
		return n.type if ( n := cls.rule_normalizers.get( name ) ) else Activity.field_type( name )

	# field resolving

	@classmethod
	def register_virtual_field( cls, *fields: VirtualField ) -> None:
		if not VirtualFields.__fields__:
			VirtualFields.__fields__ = cls.virtual_fields
		for vf in fields:
			cls.virtual_fields[vf.name] = vf
			cls.notify( EventTypes.virtual_field_registered, field=vf )

	@classmethod
	def activity_field( cls, name: str ) -> Optional[Field]:
		if f := next( (f for f in fields( Activity ) if f.name == name), None ):
			return f
		else:
			return cls.virtual_fields.get( name )

	# event handling

	@classmethod
	def notify( cls, event_type: EventTypes, *args, **kwargs ) -> None:
		for fn in Registry.event_listeners.get( event_type, [] ):
			fn( *args, **kwargs )

	@classmethod
	def register_listener( cls, event_type: EventTypes, fn: Callable ) -> None:
		if not event_type in Registry.event_listeners.keys():
			Registry.event_listeners[event_type] = []
		Registry.event_listeners.get( event_type ).append( fn )

	# handlers

	@classmethod
	def handler_for( cls, type: str ) -> Optional[Handler]:
		handler_list = Registry.handlers.get( type ) or []
		return handler_list[0] if len( handler_list ) > 0 else None

	@classmethod
	def handlers_for( cls, type: str ) -> List[Handler]:
		return Registry.handlers.get( type ) or []

	@classmethod
	def register_handler( cls, handler: Handler, type: str ) -> None:
		handler_list = Registry.handlers.get( type ) or []
		if handler not in handler_list:
			handler_list.append( handler )
			Registry.handlers[type] = handler_list
			log.debug( f'registered handler {handler.__class__} for type {type}' )

	# importers

	@classmethod
	def importer_for( cls, type: str ) -> Optional[Importer]:
		return next( iter( Registry.importers.get( type, [] ) ), None )

	@classmethod
	def importers_for( cls, type: str ) -> List[Importer]:
		return Registry.importers.get( type, [] )

	@classmethod
	def importers_for_suffix( cls, suffix: str ) -> List[Importer]:
		importers = []
		for key, value in Registry.importers.items():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ) or match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				# g1, g2, g3 = m.groups()
				if '+' in key:
					importers = value + importers
				else:
					importers.extend( value )
		return importers

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

# helpers to access registry information

def service_names() -> List[str]:
	return list( Registry.services.keys() )

def service_for( uid: Union[str, UID] ) -> Optional[Service]:
	uid = UID( uid ) if type( uid ) is str else uid
	return Registry.services.get( uid.classifier )

# decorators

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

def _fnspec( func: Callable ) -> Tuple[str, str, str, Any]:
	"""
	Helper for examining a provided function. Returns a tuple containing
	(function name, module name, qualified name, return value type)

	:param func: function to be examined
	:return: tuple
	"""
	members = getmembers( func )
	name = next( m[1] for m in members if m[0] == '__name__' )
	module = next( m[1] for m in members if m[0] == '__module__' )
	qname = next( m[1] for m in members if m[0] == '__qualname__' )
	return_type = next( m[1].get( 'return' ) for m in members if m[0] == '__annotations__' )
	return name, module, qname, return_type

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

def _register_function( *args, **kwargs ) -> Callable:
	"""
	Used for registering a function in a provided dictionary with a provided name. Valid examples:
	@decorator, @decorator( 'name' ) or @decorator( name = 'name' )
	"""
	_decorator_name = kwargs.get( '_decorator_name', 'None' ) # name of the decorator, only used for logging
	_mapping = kwargs.get( '_mapping' ) # mapping to use for registering the function
	_parameter = None

	def _inner( *inner_args ):
		inner_module, inner_name = _spec( inner_args[0] )
		_mapping[_parameter] = inner_args[0]
		log.debug( f'registered {_decorator_name} function from {inner_module}#{inner_name} with parameter {_parameter}' )
		return _parameter

	if len( args ) == 1 and isfunction( args[0] ): # case: decorated function without arguments
		module, name = _spec( args[0] )
		_mapping[name] = args[0]
		log.debug( f'registered {_decorator_name} function from {module}#{name}' )
		return args[0]
	elif len( args ) == 1 and type( args[0] ) is str: # case: decorated function with single parameter, args[0] contains the sole parameter
		_parameter = args[0]
		return _inner
	elif 'name' in kwargs:
		_parameter = kwargs.get( 'name' )
		return _inner

# hm, works but doesn't feel nice, especially for using global helper variables
def virtualfield( *args, **kwargs ):
	global _ARGS, _KWARGS
	_ARGS, _KWARGS = args, kwargs

	def _inner( *inner_args ):
		global _KWARGS
		inner_name, inner_mod, inner_qname, inner_rtype = _fnspec( inner_args[0] )
		Registry.register_virtual_field( vfield( **{ 'name': inner_name, 'type': inner_rtype, 'default': inner_args[0], **_KWARGS } ) )
		return inner_args[0]

	if len( args ) == 1 and isfunction( args[0] ): # case: decorated function without arguments
		name, mod, qname, rtype = _fnspec( args[0] )
		Registry.register_virtual_field( vfield( name=name, type=rtype, default=args[0] ) )
		return args[0]
	elif len( args ) == 0 and len( kwargs ) > 0:
		_ARGS, _KWARGS = args, kwargs
		return _inner

# maybe we should go this way for decorators ... lots of copy and paste, but cleaner code ...
def normalizer( *args, **kwargs ):
	def _inner( *inner_args ):
		Registry.register_normalizer( Normalizer( name=_fnspec( inner_args[0] )[0], type=kwargs.get( 'type' ), description=kwargs.get( 'description' ), fn=inner_args[0] ) )
		return inner_args[0]

	if args and isfunction( args[0] ): # case: decorated function without arguments
		Registry.register_normalizer( Normalizer( name=_fnspec( args[0] )[0], fn=args[0] ) )
		return args[0]
	elif kwargs and 'description' in kwargs:
		return _inner

def resourcetype( *args, **kwargs ):
	def reg_resource_type( cls ):
		Registry.register_resource_type( ResourceType( activity_cls = cls, **kwargs ) )
		Registry.dataclass_factory.schemas[cls] = Schema( omit_default=True, skip_internal=True, unknown='unknown' )
		return cls
	return reg_resource_type if len( args ) == 0 else args[0]

def service( cls: Type ):
	if isclass( cls ):
		module, name = _spec( cls )
		Registry.service_classes[module] = cls
		log.debug( f'registered service class {cls}' )
		return cls
	else:
		raise RuntimeError( 'only classes can be used with the @service decorator' )

def setup( fn: Callable ):
	if isfunction( fn ):
		module, name = _spec( fn )
		Registry.setup_functions[module] = fn
		log.debug( f'registered setup function {module}#{name}' )
		return fn
	else:
		raise RuntimeError( 'only functions can be used with the @setup decorator' )

def document( *args, **kwargs ):
	def document_class( cls ):
		if isclass( cls ):
			if document_type := kwargs.get( 'type' ):
				Registry.document_types[document_type] = cls
				log.debug( f"registered document class {cls} with type {document_type}" )

			if document_namespace := kwargs.get( 'namespace' ):
				Registry.document_classes[document_namespace] = cls
				log.debug( f"registered document class {cls} with namespace {document_namespace}" )

			return cls
		else:
			raise RuntimeError( 'only classes can be used with the @document decorator' )

	if len( args ) == 0:
		return document_class
	elif len( args ) == 1 and isclass( args[0] ):
		module_arg, name_arg = _spec( args[0] )
		Registry.document_classes[module_arg] = args[0]
		log.debug( f'registered document class {args[0]} with namespace {module_arg}' )
		return args[0]
	else:
		raise RuntimeError( 'only classes can be used with the @document decorator' )

def importer( *args, **kwargs ):
	def importer_cls( cls ):
		try:
			_importer = cls()
			_importer.type = _importer.type if _importer.type else kwargs['type']
			if 'activity_cls' in kwargs:
				_importer.activity_cls = kwargs['activity_cls']
			Registry.register_importer( _importer, _importer.type )
			Registry.register_resource_type( ResourceType( **kwargs ) )
			return cls
		except (KeyError, NameError, TypeError) as ex:
			log.error( 'improper use of @importer decorator', exc_info=True )
			raise RuntimeError( f'improper use of @importer decorator on {cls} with kwargs = {kwargs}' )

	# return importer_cls if (not args and kwargs) else importer_cls( args[0] )
	if not args and kwargs:
		return importer_cls
	elif args:
		importer_cls( args[0] )
	else:
		raise RuntimeError( f'error in decorator @importer: {args}, {kwargs} (this should not happen!)' ) # should not happen

def load( plugin_pkgs: List[str] = None, disabled: List[str] = None, ctx: ApplicationContext = None ):
	plugin_pkgs = plugin_pkgs if plugin_pkgs else [NS_PLUGINS]
	disabled = disabled if disabled else []

	for plugin_pkg in plugin_pkgs:
		plugins_module = import_module( plugin_pkg )
		for finder, name, ispkg in walk_packages( plugins_module.__path__ ):
			try:
				if not ctx.config['plugins'][name]['enabled'].get() or name in disabled:
					log.debug( f'skipping import of disabled plugin {name} in package {plugin_pkg}' )
					continue
			except NotFoundError:
				pass

			qname = f'{plugin_pkg}.{name}'
			try:
				log.debug( f'importing plugin {qname}' )
				plugin = import_module( qname )
				Registry.notify( EventTypes.plugin_loaded, plugin )
			except ModuleNotFoundError:
				log.error( f'error imporing module {qname}', exc_info=True )

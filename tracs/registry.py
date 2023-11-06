
from __future__ import annotations

from enum import Enum
from inspect import getmembers, isclass, isfunction, signature as getsignature
from logging import getLogger, INFO
from pathlib import Path
from re import match
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from attrs import Attribute, define, field, fields

from tracs.activity import Activity
from tracs.config import ApplicationContext
from tracs.core import Keyword, Normalizer, VirtualField, VirtualFields
from tracs.handlers import ResourceHandler
from tracs.protocols import Importer, Service
from tracs.resources import ResourceType
from tracs.uid import UID

log = getLogger( __name__ )

# todo: mute this logger
log.setLevel( INFO )

class EventTypes( Enum ):

	keyword_registered = 'keyword_registered'
	plugin_loaded = 'plugin_loaded'
	resource_loaded = 'resource_loaded'
	rule_normalizer_registered = 'rule_normalizer_registered'
	service_created = 'service_created'
	virtual_field_registered = 'virtual_field_registered'

@define( init=False )
class Registry:

	_instance: ClassVar[Registry] = None

	_importers: Dict[str, ResourceHandler] = field( factory=dict, alias='_importers' )
	_keywords: Dict[str, Keyword] = field( factory=dict, alias='_keywords' )
	_listeners: Dict[EventTypes, List[Callable]] = field( factory=dict, alias='_listeners' )
	_normalizers: Dict[str, Normalizer] = field( factory=dict, alias='_normalizers' )
	_resource_types: Dict[str, ResourceType] = field( factory=dict, alias='_resource_types' )
	_services: Dict[str, Service] = field( factory=dict, alias='_services' )
	_setups: Dict[str, Callable] = field( factory=dict, alias='_setups' )
	_virtual_fields: VirtualFields = field( factory=VirtualFields )

	_importer_cls: List[Tuple] = field( factory=list, alias='_importer_cls' )
	_keyword_fns: List[Tuple] = field( factory=list, alias='_keyword_fns' )
	_normalizer_fns: List[Tuple] = field( factory=list, alias='_normalizer_fns' )
	_resource_type_cls: List[Tuple] = field( factory=list, alias='_resource_type_cls' )
	_service_cls: List[Tuple] = field( factory=list, alias='_service_cls' )
	_setup_fns: List[Tuple] = field( factory=list, alias='_setup_fns' )
	_virtual_fields_fns: List[Tuple] = field( factory=list, alias='_virtual_fields_fns' )

	@classmethod
	def instance( cls, *args, **kwargs ) -> Registry:
		if cls._instance is None:
			cls._instance = super( Registry, cls ).__new__( cls, *args, **kwargs )
			# noinspection PyUnresolvedReferences
			cls._instance.__attrs_init__( *args, **kwargs )

		cls._instance.setup( *args, **kwargs )

		return cls._instance

	# constructor is not allowed
	def __init__( self ):
		raise RuntimeError( f'instance can only be created by using {self.__class__}.instance( cls ) method' )

	def __setup_keywords__( self ):
		for fn, args, kwargs in self._keyword_fns:
			try:
				name, modname, qname, params, rval = _fnspec( fn )
				kw = fn()
				if isinstance( kw, Keyword ):
					self._keywords[kw.name] = kw
					log.debug( f'registered keyword [orange1]{kw.name}[/orange1] from module [orange1]{modname}[/orange1] with static expression' )
				else:
					self._keywords[name] = Keyword( name=name, description=kwargs.get( 'description' ), fn=fn )
					log.debug( f'registered keyword [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1] with function' )

			except RuntimeError:
				log.error( f'unable to register keyword from function {fn}' )

	def __setup_normalizers__( self ):
		for fn, args, kwargs in self._normalizer_fns:
			try:
				name, modname, qname, params, rval = _fnspec( fn )
				if not params and rval == Normalizer:
					nrm = fn()
					self._normalizers[nrm.name] = nrm
					log.debug( f'registered normalizer [orange1]{nrm.name}[/orange1] from module [orange1]{modname}[/orange1]' )
				else:
					self._normalizers[name] = Normalizer( name=name, type=kwargs.get( 'type' ), description=kwargs.get( 'description' ), fn=fn )
					log.debug( f'registered normalizer [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register normalizer from function {fn}' )

	def __setup_resource_types__( self ):
		for fncls, args, kwargs in self._resource_type_cls:
			try:
				if isfunction( fncls ):
					self._resource_types[rt.type] = (rt := fncls())
				elif isclass( fncls ):
					self._resource_types[rt.type] = (rt := ResourceType( **kwargs, activity_cls=fncls ) )

				# noinspection PyUnboundLocalVariable
				log.debug( f'registered resource type [orange1]{_qname( fncls )}[/orange1] for type [orange1]{rt.type}[/orange1]' )

			except (RuntimeError, UnboundLocalError):
				log.error( f'unable to register resource type from {fncls}' )

	def __setup_importers__( self ):
		for fncls, args, kwargs in self._importer_cls:
			try:
				i = fncls()
				t = i.TYPE or kwargs.get( 'type' )
				self._importers[t] = i

				log.debug( f'registered importer [orange1]{_qname( fncls )}[/orange1] for type [orange1]{t}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register importer from {fncls}' )

	def __setup_virtual_fields__( self ):
		for fncls, args, kwargs in self._virtual_fields_fns:
			try:
				if isfunction( fncls ):
					params, rval = _params( fncls )
					if not params and rval in [VirtualField, 'VirtualField']:
						self._virtual_fields[vf.name] = (vf := fncls())
					else:
						self._virtual_fields[vf.name] = (vf := VirtualField( **{'name': _lname( fncls ), 'factory': fncls} | kwargs ))

					log.debug( f'registered virtual field [orange1]{vf.name}[/orange1] from module [orange1]{_qname( fncls )}[/orange1]' )

			except (RuntimeError, UnboundLocalError):
				log.error( f'unable to register virtual field from {fncls}' )

		# announce virtuals fields to activity class
		for k, vf in self._virtual_fields.__fields__.items():
			Activity.VF().set_field( k, vf )

	def __setup_setup_functions__( self ):
		for fn, args, kwargs in self._setup_fns:
			self._setups[_fnspec( fn )[1]] = fn

	def __setup_services__( self, *args, **kwargs ):
		self.setup_services( *args, **kwargs )

	def setup_services( self, *args, **kwargs ):
		ctx: ApplicationContext = kwargs.get( 'ctx' )
		# library: str = kwargs.get( 'library' )

		for fncls, args, kwargs in self._service_cls:
			try:
				name, modname, qname, params, rval = _fnspec( fncls )

				if ctx:
					base_path = Path( ctx.db_dir_path, name )
					overlay_path = Path( ctx.db_overlay_path, name )
					cfg, state = ctx.plugin_config_state( name, as_dict=True )

					self._services[s.name] = (s := fncls( ctx=ctx, **cfg, **state, base_path=base_path, overlay_path=overlay_path ))
					# register service name as keyword
					self._keywords[s.name] = Keyword( s.name, f'classifier "{s.name}" is contained in classifiers list', f'"{s.name}" in classifiers' )

					log.debug( f'registered service [orange1]{s.name}[/orange1] from module [orange1]{modname}[/orange1]' )

				else:
					# todo: improve this later, see github #156
					log.debug( f'skipped registering service module [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1] because of missing context' )

				# elif library: # this is mainly for test cases
				# 	base_path = Path( library, name )
				# 	overlay_path = Path( base_path.parent, 'overlay', name )
				# 	cfg, state = {}, {}
				# else: # fallback, also for test cases
				# 	base_path = Path( user_config_dir( 'tracs' ), 'db', name )
				# 	overlay_path = Path( base_path.parent.parent, 'overlay', name )
				# 	cfg, state = {}, {}



			except RuntimeError:
				log.error( f'unable to setup service from {fncls}' )

	def setup( self, *args, **kwargs ):
		if kwargs.get( 'nosetup' ) is True:
			return

		self.__setup_keywords__()
		self.__setup_normalizers__()
		self.__setup_resource_types__()
		self.__setup_importers__()
		self.__setup_virtual_fields__()
		self.__setup_setup_functions__()

		self.__setup_services__( *args, **kwargs )

	# properties

	@property
	def importers( self ) -> Mapping[str, ResourceHandler]:
		return MappingProxyType( self._importers )

	@property
	def keywords( self ) -> Mapping[str, Keyword]:
		return MappingProxyType( self._keywords )

	@property
	def normalizers( self ) -> Mapping[str, Normalizer]:
		return MappingProxyType( self._normalizers )

	@property
	def services( self ) -> Mapping[str, Service]:
		return MappingProxyType( self._services )

	@property
	def setups( self ) -> Mapping[str, Callable]:
		return MappingProxyType( self._setups )

	@property
	def resource_types( self ) -> Mapping[str, ResourceType]:
		return MappingProxyType( self._resource_types )

	@property
	def virtual_fields( self ) -> Mapping[str, VirtualField]:
		return MappingProxyType( self._virtual_fields.__fields__ )

	# services

	@classmethod
	def service_names( cls ) -> List[str]:
		return sorted( list( Registry.instance().services.keys() ) )

	@classmethod
	def service_for( cls, uid: Union[str, UID] ) -> Optional[Service]:
		uid = UID( uid ) if type( uid ) is str else uid
		return Registry.instance().services.get( uid.classifier )

	# resource types

	@classmethod
	def register_resource_type( cls, resource_type ) -> None:
		Registry.instance()._resource_types[resource_type.type] = resource_type

	# noinspection PyUnresolvedReferences
	@classmethod
	def resource_type_for_extension( cls, extension: str ) -> Optional[ResourceType]:
		return next( (rt for rt in Registry.instance().resource_types.values() if rt.extension() == extension), None )

	@classmethod
	def resource_type_for_suffix( cls, suffix: str ) -> Optional[str]:
		# first round: prefer suffix in special part of type: 'gpx' matches 'application/xml+gpx'
		for key in Registry.instance().importers.keys():
			if m := match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				return key

		# second round: suffix after slash: 'gpx' matches 'application/gpx'
		for key in Registry.instance().importers.keys():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ):
				return key

		return None

	# keywords and normalizers

	@classmethod
	def rule_normalizer_type( cls, name: str ) -> Any:
		return n.type if ( n := cls.instance().normalizers.get( name ) ) else Activity.field_type( name )

	# field resolving

	@classmethod
	def activity_field( cls, name: str ) -> Optional[Attribute]:
		if f := next( (f for f in fields( Activity ) if f.name == name), None ):
			return f
		else:
			return cls.instance().virtual_fields.get( name )

	# event handling

	@classmethod
	def notify( cls, event_type: EventTypes, *args, **kwargs ) -> None:
		for fn in Registry.instance()._listeners.get( event_type, [] ):
			fn( *args, **kwargs )

	@classmethod
	def register_listener( cls, event_type: EventTypes, fn: Callable ) -> None:
		if not event_type in Registry.instance()._listeners.keys():
			Registry.instance()._listeners[event_type] = []
		Registry.instance()._listeners.get( event_type ).append( fn )

	# importers

	@classmethod
	def importer_for( cls, type: str ) -> Optional[Importer]:
		return Registry.instance().importers.get( type )

	@classmethod
	def importers_for( cls, type: str ) -> List[Importer]:
		return Registry.instance().importers.get( type, [] )

	@classmethod
	def importers_for_suffix( cls, suffix: str ) -> List[Importer]:
		importers = []
		for key, value in Registry.instance().importers.items():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ) or match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				# g1, g2, g3 = m.groups()
				if '+' in key:
					importers = value + importers
				else:
					importers.extend( value )
		return importers

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
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._keyword_fns, __decorator_name__='keyword' )

def normalizer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._normalizer_fns, __decorator_name__='normalizer' )

def virtualfield( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._virtual_fields_fns, __decorator_name__='virtualfield' )

def importer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._importer_cls, __decorator_name__='importer' )

def resourcetype( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._resource_type_cls, __decorator_name__='resourcetype' )

def service( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._service_cls, __decorator_name__='service' )

def setup( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance()._setup_fns, __decorator_name__='setup' )

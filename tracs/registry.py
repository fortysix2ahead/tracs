
from __future__ import annotations

from enum import Enum
from inspect import getmembers, signature as getsignature
from logging import getLogger
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
from tracs.utils import unchain

log = getLogger( __name__ )

class EventTypes( Enum ):

	keyword_registered = 'keyword_registered'
	plugin_loaded = 'plugin_loaded'
	resource_loaded = 'resource_loaded'
	rule_normalizer_registered = 'rule_normalizer_registered'
	service_created = 'service_created'
	virtual_field_registered = 'virtual_field_registered'

@define
class Registry:

	_instance: ClassVar[Registry] = None

	_importers: Dict[str, List[ResourceHandler]] = field( factory=dict, alias='_importers' )
	_keywords: Dict[str, Keyword] = field( factory=dict, alias='_keywords' )
	_listeners: Dict[EventTypes, List[Callable]] = field( factory=dict, alias='_listeners' )
	_normalizers: Dict[str, Normalizer] = field( factory=dict, alias='_normalizers' )
	_resource_types: Dict[str, ResourceType] = field( factory=dict, alias='_resource_types' )
	_services: Dict[str, Service] = field( factory=dict, alias='_services' )
	_setups: Dict[str, Callable] = field( factory=dict, alias='_setups' )
	_virtual_fields: VirtualFields = field( default=Activity.VF() )

	__importer_cls__: List[Tuple] = field( factory=list, alias='__importer_cls__' )
	__keyword_fns__: List[Tuple] = field( factory=list, alias='__keyword_fns__' )
	__normalizer_fns__: List[Tuple] = field( factory=list, alias='__normalizer_fns__' )
	__resource_type_cls__: List[Tuple] = field( factory=list, alias='__resource_type_cls__' )
	__service_cls__: List[Tuple] = field( factory=list, alias='__service_cls__' )
	__setup_fns__: List[Tuple] = field( factory=list, alias='__setup_fns__' )
	__virtual_fields_fns__: List[Tuple] = field( factory=list, alias='__virtual_fields_fns__' )

	@classmethod
	def instance( cls ) -> Registry:
		if cls._instance is None:
			cls._instance = Registry()
		return cls._instance

	def __setup_keywords__( self ):
		for fn, args, kwargs in self.__keyword_fns__:
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
		for fn, args, kwargs in self.__normalizer_fns__:
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
		for fncls, args, kwargs in self.__resource_type_cls__:
			try:
				name, modname, qname, params, rval = _fnspec( fncls )
				if not params and rval in [ResourceType, 'ResourceType']: # todo: rval is 'ResourceType' for tcx.py? WTF? WHY???
					rt = fncls()
				else:
					rt = ResourceType( **kwargs )
				self._resource_types[rt.type] = rt
				log.debug( f'registered resource type [orange1]{rt.name}[/orange1] from module [orange1]{modname}[/orange1] for type [orange1]{rt.type}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register resource type from {fncls}' )

	def __setup_importers__( self ):
		for fncls, args, kwargs in self.__importer_cls__:
			try:
				name, modname, qname, params, rval = _fnspec( fncls )
				i = fncls()
				type = i.TYPE or kwargs( 'type' )
				self._importers[type] = [ *self._importers[type], i ] if type in self._importers else [i]

				log.debug( f'registered importer [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1] for type [orange1]{type}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register importer from {fncls}' )

	def __setup_virtual_fields__( self ):
		for fn, args, kwargs in self.__virtual_fields_fns__:
			try:
				name, modname, qname, params, rval = _fnspec( fn )
				if not params and rval == VirtualField:
					vf = fn()
					self._virtual_fields[vf.name] = vf
					log.debug( f'registered virtual field [orange1]{vf.name}[/orange1] from module [orange1]{modname}[/orange1]' )
				else:
					self._virtual_fields[name] = VirtualField( name=name, type=kwargs.get( 'type' ), description=kwargs.get( 'description' ),
					                                           display_name=kwargs.get( 'display_name' ), factory=fn )
					log.debug( f'registered virtual field [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register virtual field from {fn}' )

	def __setup_setup_functions__( self ):
		for fn, args, kwargs in self.__setup_fns__:
			self._setups[_fnspec( fn )[1]] = fn

	# todo: setup service here?
	def __setup_services__( self ):
		pass

	def setup_services( self, ctx: ApplicationContext ):
		for fncls, args, kwargs in self.__service_cls__:
			try:
				name, modname, qname, params, rval = _fnspec( fncls )
				base_path = Path( ctx.db_dir_path, name )
				overlay_path = Path( ctx.db_overlay_path, name )
				cfg, state = ctx.plugin_config_state( name, as_dict=True )
				s: Service = fncls( ctx=ctx, **cfg, **state, base_path=base_path, overlay_path=overlay_path )
				self._services[s.name] = s

				# register service name as keyword
				self._keywords[s.name] = Keyword( s.name, f'classifier "{s.name}" is contained in classifiers list', f'"{s.name}" in classifiers' )

				log.debug( f'registered service [orange1]{s.name}[/orange1] from module [orange1]{modname}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to setup service from {fncls}' )

	def setup( self ):
		self.__setup_keywords__()
		self.__setup_normalizers__()
		self.__setup_resource_types__()
		self.__setup_importers__()
		self.__setup_virtual_fields__()
		self.__setup_setup_functions__()
		self.__setup_services__()

	# properties

	@property
	def importers( self ) -> Mapping[str, List[ResourceHandler]]:
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
		return next( iter( Registry.instance().importers.get( type, [] ) ), None )

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

		_fncls_list.append( (fncls, args, kwargs) )
		log.debug( f'registered {_decorator_name} function/class from {fncls} in module {_fnspec( fncls )[1]}' )
		# return _wrapper
		return fncls

	if args and not kwargs and callable( args[0] ):
		_fncls_list.append( (args[0], (), {}) )
		log.debug( f'registered {_decorator_name} function from {args[0]} in module {_fnspec( args[0] )[1]}' )

	return _inner

# actual real-world decorators below

def keyword( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__keyword_fns__, __decorator_name__='keyword' )

def normalizer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__normalizer_fns__, __decorator_name__='normalizer' )

def virtualfield( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__virtual_fields_fns__, __decorator_name__='virtualfield' )

def importer( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__importer_cls__, __decorator_name__='importer' )

def resourcetype( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__resource_type_cls__, __decorator_name__='resourcetype' )

def service( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__service_cls__, __decorator_name__='service' )

def setup( *args, **kwargs ):
	return _register( *args, **kwargs, __fncls_list__ = Registry.instance().__setup_fns__, __decorator_name__='setup' )

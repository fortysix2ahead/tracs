
from __future__ import annotations

from enum import Enum
from inspect import getmembers, isclass, isfunction, signature as getsignature
from logging import getLogger
from pathlib import Path
from re import match
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Type, Union

from attrs import Attribute, define, field, fields

from tracs.activity import Activity
from tracs.config import ApplicationContext
from tracs.core import Keyword, Normalizer, VirtualField, VirtualFields
from tracs.handlers import ResourceHandler
from tracs.protocols import Importer, Service
from tracs.resources import ResourceType
from tracs.uid import UID

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

	importers: Dict[str, ResourceHandler] = field( factory=dict )
	keywords: Dict[str, Keyword] = field( factory=dict )
	listeners: Dict[EventTypes, List[Callable]] = field( factory=dict )
	normalizers: Dict[str, Normalizer] = field( factory=dict )
	resource_types: Dict[str, ResourceType] = field( factory=dict )
	services: Dict[str, Service] = field( factory=dict )
	setups: Dict[str, Callable] = field( factory=dict )
	virtual_fields: VirtualFields = field( factory=VirtualFields )

	@classmethod
	def create( cls, **kwargs ) -> Registry:
		instance = Registry()

		instance._setup_keywords( kwargs.get( 'keywords', [] ) )
		instance._setup_normalizers( kwargs.get( 'normalizers', [] ) )
		instance._setup_resource_types( kwargs.get( 'resource_types', [] ) )
		instance._setup_importers( kwargs.get( 'importers', [] ) )
		instance._setup_virtual_fields( kwargs.get( 'virtual_fields', [] ) )
		instance._setup_setups( kwargs.get( 'setups', [] ) )
		instance._setup_services( kwargs.get( 'ctx' ), kwargs.get( 'services', [] ) )

		return instance

	def _setup_keywords( self, keywords: List[Tuple] ):
		for fn, args, kwargs in keywords:
			try:
				name, modname, qname, params, rval = _fnspec( fn )
				kw = fn()
				if isinstance( kw, Keyword ):
					self.keywords[kw.name] = kw
					log.debug( f'registered keyword [orange1]{kw.name}[/orange1] from module [orange1]{modname}[/orange1] with static expression' )
				else:
					self.keywords[name] = Keyword( name=name, description=kwargs.get( 'description' ), fn=fn )
					log.debug( f'registered keyword [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1] with function' )

			except RuntimeError:
				log.error( f'unable to register keyword from function {fn}' )

	def _setup_normalizers( self, normalizers: List[Tuple] ):
		for fn, args, kwargs in normalizers:
			try:
				name, modname, qname, params, rval = _fnspec( fn )
				if not params and rval == Normalizer:
					nrm = fn()
					self.normalizers[nrm.name] = nrm
					log.debug( f'registered normalizer [orange1]{nrm.name}[/orange1] from module [orange1]{modname}[/orange1]' )
				else:
					self.normalizers[name] = Normalizer( name=name, type=kwargs.get( 'type' ), description=kwargs.get( 'description' ), fn=fn )
					log.debug( f'registered normalizer [orange1]{name}[/orange1] from module [orange1]{modname}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register normalizer from function {fn}' )

	def _setup_resource_types( self, resource_types: List[Tuple] ):
		for fncls, args, kwargs in resource_types:
			try:
				if isfunction( fncls ):
					self.resource_types[rt.type] = (rt := fncls())
				elif isclass( fncls ):
					self.resource_types[rt.type] = (rt := ResourceType( **kwargs, activity_cls=fncls ) )

				# noinspection PyUnboundLocalVariable
				log.debug( f'registered resource type [orange1]{_qname( fncls )}[/orange1] for type [orange1]{rt.type}[/orange1]' )

			except (RuntimeError, UnboundLocalError):
				log.error( f'unable to register resource type from {fncls}' )

	def _setup_importers( self, importers: List[Tuple] ):
		for fncls, args, kwargs in importers:
			try:
				i = fncls()
				t = i.TYPE or kwargs.get( 'type' )
				self.importers[t] = i

				log.debug( f'registered importer [orange1]{_qname( fncls )}[/orange1] for type [orange1]{t}[/orange1]' )

			except RuntimeError:
				log.error( f'unable to register importer from {fncls}' )

	def _setup_virtual_fields( self, virtual_fields: List[Tuple] ):
		for fncls, args, kwargs in virtual_fields:
			try:
				if isfunction( fncls ):
					params, rval = _params( fncls )
					if not params and rval in [VirtualField, 'VirtualField']:
						self.virtual_fields[vf.name] = (vf := fncls())
					else:
						self.virtual_fields[vf.name] = (vf := VirtualField( **{'name': _lname( fncls ), 'factory': fncls} | kwargs ))

					log.debug( f'registered virtual field [orange1]{vf.name}[/orange1] from module [orange1]{_qname( fncls )}[/orange1]' )

			except (RuntimeError, UnboundLocalError):
				log.error( f'unable to register virtual field from {fncls}' )

		# announce virtuals fields to activity class
		for k, vf in self.virtual_fields.__fields__.items():
			Activity.VF().set_field( k, vf )

	def _setup_setups( self, setups: List[Tuple] ):
		for fn, args, kwargs in setups:
			self.setups[_fnspec( fn )[1]] = fn

	def _setup_services( self, ctx: ApplicationContext, services: List[Tuple] ):
		for fncls, args, kwargs in services:
			try:
				name, modname, qname, params, rval = _fnspec( fncls )

				if ctx:
					base_path = Path( ctx.db_dir_path, name )
					overlay_path = Path( ctx.db_overlay_path, name )
					cfg, state = ctx.plugin_config_state( name, as_dict=True )

					self.services[s.name] = (s := fncls( ctx=ctx, **cfg, **state, base_path=base_path, overlay_path=overlay_path ))
					# register service name as keyword
					self.keywords[s.name] = Keyword( s.name, f'classifier "{s.name}" is contained in classifiers list', f'"{s.name}" in classifiers' )

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

	# services

	def service_names( self ) -> List[str]:
		return sorted( list( self.services.keys() ) )

	def service_for( self, uid: Union[str, UID] ) -> Optional[Service]:
		uid = UID( uid ) if type( uid ) is str else uid
		return self.services.get( uid.classifier )

	# resource types

	def register_resource_type( self, resource_type ) -> None:
		self.resource_types[resource_type.type] = resource_type

	def summary_types( self ) -> List[ResourceType]:
		return [ rt for rt in  self.resource_types.values() if rt.summary ]

	def recording_types( self ) -> List[ResourceType]:
		return [ rt for rt in  self.resource_types.values() if rt.recording ]

	def resource_type_for_extension( self, extension: str ) -> Optional[ResourceType]:
		return next( (rt for rt in self.resource_types.values() if rt.extension() == extension), None )

	def resource_type_for_suffix( self, suffix: str ) -> Optional[str]:
		# first round: prefer suffix in special part of type: 'gpx' matches 'application/xml+gpx'
		for key in self.importers.keys():
			if m := match( f'^(\w+)/(\w+)\+{suffix}$', key ):
				return key

		# second round: suffix after slash: 'gpx' matches 'application/gpx'
		for key in self.importers.keys():
			if m := match( f'^(\w+)/{suffix}(\+([\w-]+))?$', key ):
				return key

		return None

	# keywords and normalizers

	def rule_normalizer_type( self, name: str ) -> Any:
		return n.type if ( n := self.normalizers.get( name ) ) else Activity.field_type( name )

	# field resolving

	def activity_field( self, name: str ) -> Optional[Attribute]:
		if f := next( (f for f in fields( Activity ) if f.name == name), None ):
			return f
		else:
			return self.virtual_fields.get( name )

	# event handling

	def notify( self, event_type: EventTypes, *args, **kwargs ) -> None:
		for fn in self.listeners.get( event_type, [] ):
			fn( *args, **kwargs )

	def register_listener( self, event_type: EventTypes, fn: Callable ) -> None:
		if not event_type in self.listeners.keys():
			self.listeners[event_type] = []
		self.listeners.get( event_type ).append( fn )

	# importers

	def importer_for( self, type: str ) -> Optional[Importer]:
		return self.importers.get( type )

	def importers_for( self, type: str ) -> List[Importer]:
		return self.importers.get( type, [] )

	def importers_for_suffix( self, suffix: str ) -> List[Importer]:
		importers = []
		for key, value in self.importers.items():
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

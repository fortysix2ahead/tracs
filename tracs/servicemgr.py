from logging import getLogger
from typing import Any, Dict, List, Optional, Type

from attrs import define, field
from more_itertools import first_true

from tracs.constants import CFG_CTX
from tracs.protocols import Resource, Service
from uid import UID

log = getLogger( __name__ )

@define
class ServiceManager:

	services_classes: Dict[str, Type[Service]] = field( factory=dict )
	services: Dict[str, Service] = field( factory=dict )

	def add_class( self, cls: Type[Service] ):
		"""
		Adds a service class to the manager.
		The class is used to create service instances when configured and actually used.

		:param cls: service class to add
		"""
		self.services_classes[f'{cls.__module__}.{cls.__name__}'] = cls

	def add( self, service_instance: Service ) -> None:
		"""
		Adds an existing service to the manager.

		:param service_instance: service instance to add
		:return: None
		"""
		self.services[service_instance.name] = service_instance

	def add_from( self, ctx, name: str, config: Dict[str, Any] ):
		service_cls = first_true( self.services_classes.values(), pred=lambda sc: sc.SERVICE_NAME == config.get( 'type' ) )
		if service_cls:
			cfg_dict = config | { CFG_CTX: ctx, 'name': name }
			cfg_dict.pop( 'type' )
			self.services[name] = service_cls( **cfg_dict )
		else:
			log.error( f'unable to find service class for service type {name}' )

	def get( self, name: str ) -> Service|None:
		return self.services.get( name )

	def service_names( self ) -> List[str]:
		return list( self.services.keys() )

	# noinspection PyMethodMayBeStatic
	def path_for( self, resource: Resource ) -> str:
		return resource.path # todo: this might be removed

	def url_for( self, uid: UID|str ) -> Optional[str]:
		uid: UID = UID( uid ) if isinstance( uid, str ) else uid
		if service := self.services.get( uid.classifier ):
			return service.url_for( local_id=uid.local_id )
		else:
			return None

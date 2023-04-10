
from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Type

from dataclass_factory import Factory
from requests import Response
from requests import Session

from .activity import Activity
from .resources import Resource

log = getLogger( __name__ )

class ResourceHandler:

	def __init__( self, resource_type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		self._activity_cls: Optional[Type] = activity_cls
		self._type: Optional[str] = resource_type
		self._factory: Factory = Factory( debug_path=True, schemas={} )
		self.content: Optional[bytes] = None
		self.resource: Optional[Resource] = None
		self.data: Any = None

	def load( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Resource]:
		# load from either path or url
		if path:
			self.resource = self.load_from_path( path, **kwargs )
		elif url:
			self.resource = self.load_from_url( url, **kwargs )
		else:
			return None

		# try transform content in resource into structured data (i.e. from bytes to a dict)
		# by default this does nothing and has to be implemented in subclasses
		# this method expects that the attribute resource.raw is populated
		self.load_data( self.resource, **kwargs )

		# postprocess data
		# if resource.raw is dict-like and there's a dataclass class factory and a class
		# the factory will be used to transfrom the data from raw and populate the data field
		# if not, data will be set to raw
		self.postprocess_data( self.resource, **kwargs )

		# return the result
		return self.resource

	def load_as_activity( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Activity]:
		return self.as_activity( self.load( path, url, **kwargs ) )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		if self.activity_cls:
			return self._factory.load( resource.raw, self.activity_cls )
		else:
			return None

	def load_from_url( self, url: str, **kwargs ) -> Optional[Resource]:
		session: Session = kwargs.get( 'session' )
		headers = kwargs.get( 'headers' )
		allow_redirects: bool = kwargs.get( 'allow_redirects', True )
		stream: bool = kwargs.get( 'stream', True )

		response: Response = session.get( url, headers=headers, allow_redirects=allow_redirects, stream=stream )
		return Resource(
			type=self._type,
			source=url,
			status=response.status_code,
			content=response.content,
		)

	def load_from_path( self, path: Path, **kwargs ) -> Optional[Resource]:
		return Resource(
			type=self._type,
			path=path.name,
			source=path.as_uri(),
			status=200,
			content=path.read_bytes()
		)

	def load_data( self, resource: Resource, **kwargs ) -> None:
		pass

	def postprocess_data( self, resource: Resource, **kwargs ) -> None:
		try:
			if isinstance( resource.raw, dict ) and self._activity_cls:
				resource.data = self._factory.load( resource.raw, self._activity_cls )
			else:
				resource.data = resource.raw
		except RuntimeError:
			log.error( f'unable to transform resource content into structured data by using the factory for {self._activity_cls}', exc_info=True )

	# noinspection PyMethodMayBeStatic
	def as_str( self, content: bytes, encoding: str = 'UTF-8' ) -> str:
		return content.decode( encoding )

	# noinspection PyMethodMayBeStatic
	def as_bytes( self, text: str, encoding: str = 'UTF-8' ) -> bytes:
		return text.encode( encoding )

	@property
	def type( self ) -> Optional[str]:
		return self._type

	@type.setter
	def type( self, value: str ) -> None :
		self._type = value

	@property
	def activity_cls( self ) -> Optional[Type]:
		return self._activity_cls

	@activity_cls.setter
	def activity_cls( self, cls: Type ) -> None:
		self._activity_cls = cls

	# noinspection PyMethodMayBeStatic
	def preprocess_data( self, data: Any, **kwargs ) -> Any:
		return data

	def save_data( self, data: Any, **kwargs ) -> bytes:
		pass

	# noinspection PyMethodMayBeStatic
	def save_to_path( self, content: bytes, path: Path, **kwargs ) -> None:
		path.write_bytes( content )

	# noinspection PyMethodMayBeStatic
	def save_to_url( self, content: bytes, url: str, **kwargs ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def save_to_resource( self, content: bytes, **kwargs ) -> Resource:
		data = kwargs.get( 'data' )
		uid = kwargs.get( 'uid' )
		resource_path = kwargs.get( 'resource_path' )
		resource_type = kwargs.get( 'resource_type' )
		source = kwargs.get( 'source' )
		status = kwargs.get( 'status' )
		summary = kwargs.get( 'summary' )

		return Resource( raw=data, content=content, uid=uid, path=resource_path, source=source, status=status, summary=summary, type=resource_type )

	def save( self, data: Any, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Resource]:
		# allow sub classes to preprocess data
		data = self.preprocess_data( data )

		content: bytes = self.save_data( data, **kwargs )

		if path:
			self.save_to_path( content, path, **kwargs )
		elif url:
			self.save_to_url( content, url, **kwargs )
		else:
			return self.save_to_resource( content, data=data, **kwargs )

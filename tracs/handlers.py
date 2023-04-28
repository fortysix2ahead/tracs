
from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any, Union
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

		self.resource: Optional[Resource] = None
		self.content: Optional[Union[bytes,str]] = None
		self.raw: Any = None
		self.data: Any = None

	def load( self, path: Optional[Path] = None, url: Optional[str] = None, content: Optional[bytes] = None,  **kwargs ) -> Optional[Resource]:
		# load from either path, url or content
		if path:
			self.content = self.load_from_path( path, **kwargs )
		elif url:
			self.content = self.load_from_url( url, **kwargs )
		elif content:
			self.content = content
		else:
			return None

		# try to transform content into structured data (i.e. from bytes to a dict)
		# by default this does nothing and has to be implemented in subclasses
		self.raw = self.load_data( self.content, **kwargs )

		# postprocess data
		# if resource.raw is dict-like and there's a dataclass class factory and a class
		# the factory will be used to transfrom the data from raw and populate the data field
		# if not, data will be set to raw
		self.data = self.postprocess_data( self.raw, **kwargs )

		# return the result
		return self.create_resource( path, url, **kwargs )

	def load_as_activity( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Activity]:
		if resource := kwargs.get( 'resource' ):
			# lazy (re-)loading of an existing resource
			if resource.content and resource.raw is None and resource.data is None:
				resource.raw = self.load_data( resource.content )

			if resource.raw is not None and resource.data is None:
				resource.data = self.postprocess_data( resource.raw )

			if resource.data:
				return self.as_activity( resource )
			else:
				return None

		else:
			return self.as_activity( self.load( path, url, **kwargs ) )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		return self._factory.load( resource.raw, self.activity_cls ) if self.activity_cls else None

	# noinspection PyMethodMayBeStatic
	def load_from_url( self, url: str, **kwargs ) -> Optional[bytes]:
		session: Session = kwargs.get( 'session' )
		headers = kwargs.get( 'headers' )
		allow_redirects: bool = kwargs.get( 'allow_redirects', True )
		stream: bool = kwargs.get( 'stream', True )
		response: Response = session.get( url, headers=headers, allow_redirects=allow_redirects, stream=stream )
		return response.content

	# noinspection PyMethodMayBeStatic
	def load_from_path( self, path: Path, **kwargs ) -> Optional[bytes]:
		return path.read_bytes()

	def load_data( self, content: Union[bytes,str], **kwargs ) -> Any:
		pass

	def postprocess_data( self, raw: Any, **kwargs ) -> Any:
		try:
			if isinstance( raw, dict ) and self._activity_cls:
				return self._factory.load( raw, self._activity_cls )
			else:
				return raw
		except RuntimeError:
			log.error( f'unable to transform resource content into structured data by using the factory for {self._activity_cls}', exc_info=True )

	def create_resource( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Resource:
		return Resource(
			type = self._type,
			path = path.name if path else None, # todo: use url here as well?
			source = path.as_uri() if path else url,
			content = self.content,
			raw = self.raw,
			data = self.data
		)

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
		return Resource(
			raw = kwargs.get( 'raw' ),
			data = kwargs.get( 'data' ),
			content = content,
			uid = kwargs.get( 'uid' ),
			path = kwargs.get( 'resource_path' ),
			source = kwargs.get( 'source' ),
			status = kwargs.get( 'status' ),
			summary = kwargs.get( 'summary' ),
			type = kwargs.get( 'resource_type' ),
		)

	def save( self, data: Any, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Resource]:
		# allow sub classes to preprocess data
		raw = self.preprocess_data( data )

		content: bytes = self.save_data( raw, **kwargs )

		if path:
			self.save_to_path( content, path, **kwargs )
		elif url:
			self.save_to_url( content, url, **kwargs )
		else:
			return self.save_to_resource( content, raw=raw, data=data, **kwargs )

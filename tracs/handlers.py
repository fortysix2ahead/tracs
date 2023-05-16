
from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any, Optional, Type, Union

from dataclass_factory import Factory
from requests import Response, Session

from tracs.activity import Activity
from tracs.resources import Resource

log = getLogger( __name__ )

class ResourceHandler:

	resource_type: Optional[str] = None

	def __init__( self, resource_type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		self._type: Optional[str] = resource_type
		self._activity_cls: Optional[Type] = activity_cls
		# todo: factoty field could be moved into JSON handler, same may be true for activity_cls field
		self._factory: Factory = Factory( debug_path=True, schemas={} )

		# todo: are these fields really needed? probably not ...
		self.resource: Optional[Resource] = None
		self.content: Optional[Union[bytes,str]] = None
		self.raw: Any = None
		self.data: Any = None

	def load( self, path: Optional[Path] = None, url: Optional[str] = None, content: Optional[bytes] = None, **kwargs ) -> Optional[Resource]:
		# load from either from path, url or provided content
		if content:
			self.content = self.load_from_content( content, **kwargs )
		elif path:
			self.content = self.load_from_path( path, **kwargs )
		elif url:
			self.content = self.load_from_url( url, **kwargs )

		# try to transform content into structured data (i.e. from bytes to a dict)
		# by default this does nothing and has to be implemented in subclasses
		self.raw = self.load_raw( self.content, **kwargs )

		# postprocess data
		# if resource.raw is dict-like and there's a dataclass class factory and a class
		# the factory will be used to transfrom the data from raw and populate the data field
		# if not, data will be set to raw
		self.data = self.load_data( self.raw, **kwargs )

		# return the result
		return self.load_resource( path, url, **kwargs )

	def load_as_activity( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Activity]:
		if resource := kwargs.get( 'resource' ):
			# lazy (re-)loading of an existing resource
			if resource.content and resource.raw is None and resource.data is None:
				resource.raw = self.load_raw( resource.content )

			if resource.raw is not None and resource.data is None:
				resource.data = self.load_data( resource.raw )

			if resource.data:
				return self.as_activity( resource )
			else:
				return None

		else:
			return self.as_activity( self.load( path, url, **kwargs ) )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		return self._factory.load( resource.raw, self.activity_cls ) if self.activity_cls else None

	# load methods

	# noinspection PyMethodMayBeStatic
	def load_from_content( self, content: Union[bytes,str], **kwargs ) -> Optional[Union[bytes, str]]:
		"""
		By default, this does nothing. Only returns the content, subclasses may override.
		"""
		return content

	# noinspection PyMethodMayBeStatic
	def load_from_path( self, path: Path, **kwargs ) -> Optional[bytes]:
		"""
		Reads from the provided path and returns the files content as bytes.
		"""
		return path.read_bytes()

	# noinspection PyMethodMayBeStatic
	def load_from_url( self, url: str, **kwargs ) -> Optional[bytes]:
		session: Session = kwargs.get( 'session' )
		headers = kwargs.get( 'headers' )
		allow_redirects: bool = kwargs.get( 'allow_redirects', True )
		stream: bool = kwargs.get( 'stream', True )
		response: Response = session.get( url, headers=headers, allow_redirects=allow_redirects, stream=stream )
		return response.content

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		"""
		Loads raw data from provided content.
		Example: load a json from a string and return a dict.
		"""
		pass

	def load_data( self, raw: Any, **kwargs ) -> Any:
		"""
		Transforms raw data into structured data. If raw data is a dict and an activity class is set, it will use
		the dataclass factory to try a transformation. Will return raw data in case that fails.
		Example: transform a dict into a dataclass.
		"""
		try:
			if isinstance( raw, dict ) and self._activity_cls:
				return self._factory.load( raw, self._activity_cls )
			else:
				return raw
		except RuntimeError:
			log.error( f'unable to transform raw data into structured data by using the factory for {self._activity_cls}', exc_info=True )

	def load_resource( self, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Resource:
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
	def save_data( self, data: Any, **kwargs ) -> Any:
		"""
		Transforms structured data into raw data, for instance from a dataclass to a dict.
		By default, this simply returns the data and may be overridden in subclasses.
		"""
		if self._activity_cls:
			try:
				return self._factory.dump( data, self._activity_cls )
			except RuntimeError:
				log.error( f'unable to transform raw data into structured data by using the factory for {self._activity_cls}', exc_info=True )
				return data
		else:
			return data

	def save_raw( self, data: Any, **kwargs ) -> bytes:
		"""
		Transforms raw data into bytes.
		By default, this calls __repr__() and encodes the result with UTF-8.
		This method is supposed to be implemented in subclasses.
		"""
		return data.__repr__().encode( 'UTF-8' )

	# noinspection PyMethodMayBeStatic
	def save_to_path( self, content: bytes, path: Path, **kwargs ) -> None:
		path.write_bytes( content )

	# noinspection PyMethodMayBeStatic
	def save_to_url( self, content: bytes, url: str, **kwargs ) -> None:
		raise NotImplementedError

	# noinspection PyMethodMayBeStatic
	def save_to_resource( self, content, raw, data, **kwargs ) -> Resource:
		return Resource( raw = raw, data = data, content = content, **kwargs )

	def save( self, data: Any, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Resource]:
		raw = self.save_data( data )

		content = self.save_raw( raw, **kwargs )

		if path:
			self.save_to_path( content, path, **kwargs )
		elif url:
			self.save_to_url( content, url, **kwargs )

		return self.save_to_resource( content=content, raw=raw, data=data, **kwargs )


from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any, Callable, Optional, Type, Union

from fs.base import FS
from fs.path import basename
from requests import Response, Session

from tracs.activity import Activity
from tracs.resources import Resource

log = getLogger( __name__ )

class ResourceHandler:

	# todo: remove resource_type in favour of TYPE
	resource_type: Optional[str] = None
	TYPE: Optional[str] = resource_type
	ACTIVITY_CLS: Optional[Type] = None

	def __init__( self, resource_type: Optional[str] = None, activity_cls: Optional[Type] = None ) -> None:
		self._type: Optional[str] = resource_type
		self._activity_cls: Optional[Type] = activity_cls
		self._factory: Callable = self.transform_data

		# todo: are these fields really needed? probably not ...
		self.resource: Optional[Resource] = None
		self.content: Optional[Union[bytes,str]] = None
		self.raw: Any = None
		self.data: Any = None

	def load( self, path: Optional[Union[Path, str]] = None, url: Optional[str] = None, content: Optional[bytes] = None, fs: Optional[FS] = None, **kwargs ) -> Optional[Resource]:
		# load from either from path, url or provided content
		if content:
			self.content = self.load_from_content( content, **kwargs )
		elif path:
			if fs:
				self.content = self.load_from_fs( fs, path, **kwargs )
			else:
				self.content = self.load_from_path( path, **kwargs )
		elif url:
			self.content = self.load_from_url( url, **kwargs )

		# try to transform content into structured data (i.e. from bytes to a dict)
		# by default this does nothing and has to be implemented in subclasses
		self.raw = self.load_raw( self.content, **kwargs )

		# postprocess data
		# if resource.raw is dict-like  structure and there's a factory function,
		# the factory will be used to transfrom the data from raw and populate the data field
		# if not, the data field will be set to raw
		self.data = self.load_data( self.raw, **kwargs )

		# return the result
		return self.load_resource( path, url, **kwargs )

	def load_as_activity( self, path: Optional[Union[Path, str]] = None, url: Optional[str] = None, fs: Optional[FS] = None, **kwargs ) -> Optional[Activity]:
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
			return self.as_activity( self.load( path=path, url=url, fs=fs, **kwargs ) )

	# todo: leave this method empty?
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
	def load_from_fs( self, fs: FS, path: str, **kwargs ) -> Optional[bytes]:
		return fs.readbytes( path )

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
		Transforms raw data into structured data.
		This assumes that self._factory is a function which can be called with raw data as an argument.
		The function should follow the convention: fn( raw_data, **kwargs ). kwargs will contain activity_cls as optional arg.
		This method will return raw if the call to the factory function fails.
		"""
		if self._factory is not None:
			try:
				return self._factory( raw, activity_cls=self._activity_cls )
			except RuntimeError:
				log.error( f'unable to transform raw data into structured data using the factory function', exc_info=True )

		return raw

	# noinspection PyMethodMayBeStatic
	def transform_data( self, raw: Any, **kwargs ):
		return raw

	def load_resource( self, path: Optional[Union[Path,str]] = None, url: Optional[str] = None, **kwargs ) -> Resource:
		if isinstance( path, Path ):
			path, source = path.name, path.as_uri()
		elif isinstance( path, str ):
			path, source = basename( path ), None
		else:
			path, source = None, None

		if resource := kwargs.get( 'resource' ):
			resource.content = self.content
			resource.raw = self.raw
			resource.data = self.data
		else:
			resource = Resource( type=self.__class__.TYPE, path=path, source=source, content=self.content, raw=self.raw, data=self.data )

		return resource

	# noinspection PyMethodMayBeStatic
	def as_str( self, content: bytes, encoding: str = 'UTF-8' ) -> str:
		return content.decode( encoding )

	# noinspection PyMethodMayBeStatic
	def as_bytes( self, text: str, encoding: str = 'UTF-8' ) -> bytes:
		return text.encode( encoding )

	@property
	def type( self ) -> Optional[str]:
		return self.__class__.TYPE

	@type.setter
	def type( self, value: str ) -> None :
		self._type = value

	@property
	def activity_cls( self ) -> Optional[Type]:
		return self.__class__.ACTIVITY_CLS

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


from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Protocol
from typing import Type
from typing import Union

class ResourceStatus( Enum ):
	UNKNOWN = 100
	EXISTS = 200
	NO_CONTENT = 204
	NOT_FOUND = 404

class Resource( Protocol ):

	@property
	@abstractmethod
	def name( self ) -> str:
		pass

	@property
	@abstractmethod
	def type( self ) -> str:
		pass

	@property
	@abstractmethod
	def status( self ) -> int:
		pass

	@status.setter
	@abstractmethod
	def status( self, status: int ) -> None:
		pass

	@property
	@abstractmethod
	def path( self ) -> str:
		pass

	@property
	@abstractmethod
	def uid( self ) -> str:
		pass

	@property
	@abstractmethod
	def content( self ) -> Optional[bytes]:
		pass

	@property
	@abstractmethod
	def text( self ) -> Optional[str]:
		pass

	@property
	@abstractmethod
	def raw( self ) -> Any:
		pass

	@property
	@abstractmethod
	def data( self ) -> Any:
		pass

class Activity( ABC, dict ):
	"""
	Abstract base class for an activity.
	"""

	@property
	@abstractmethod
	def id( self ) -> int:
		pass

	@property
	@abstractmethod
	def uid( self ) -> str:
		pass

	@property
	@abstractmethod
	def raw( self ) -> Any:
		pass

	@property
	@abstractmethod
	def raw_id( self ) -> int:
		pass

	@property
	@abstractmethod
	def raw_data( self ) -> Union[str, bytes]:
		pass

	@property
	@abstractmethod
	def raw_name( self ) -> str:
		pass

	@property
	@abstractmethod
	def resources( self ) -> List[Resource]:
		pass

class Service( Protocol ):
	"""
	Protocol for a service being able to fetch activities/resource from (remote) sources.
	"""

	@abstractmethod
	def login( self ) -> bool:
		pass

	@abstractmethod
	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.
		The returned path must point to a directory.

		:param activity: activity
		:param resource: resource
		:param ext: file extension for which the path should be returned, can be None
		:return: path of the activity/resource in the local file system
		"""
		pass

	@abstractmethod
	def path_for_id( self, raw_id: int, base_path: Optional[Path] ) -> Path:
		pass

	@abstractmethod
	def link_for( self, activity: Optional[Activity], resource: Optional[Resource], ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the link path for an activity or resource.

		:param activity: activity to link
		:param resource: resource to link
		:param ext: file extension (deprecated)
		:return: link path for activity or None if no path can be calculated
		"""
		pass

	def url_for( self, activity: Optional[Activity], resource: Optional[Resource], local_id: Optional[int] ) -> Optional[str]:
		"""
		Return the URL either for the provided activity or resource.

		:param activity: activity to retrieve the URL for
		:param resource: resource to retrieve the URL for
		:param local_id: local id to retrieve the URL for
		:return: URL or None if URL cannot be determined
		"""

	@abstractmethod
	def import_activities( self, force: bool, pretend: bool, **kwargs ):
		pass

	@abstractmethod
	def fetch( self, force: bool, pretend: bool, **kwargs ) -> Union[List[Activity], List[Resource]]:
		pass

	@abstractmethod
	def download( self, activity: Optional[Activity], summary: Optional[Resource], force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		pass

	@abstractmethod
	def postprocess( self, activity: Optional[Activity], resources: Optional[List[Resource]], **kwargs ) -> None:
		pass

	@abstractmethod
	def link( self, activity: Activity, resource: Resource, force: bool, pretend: bool, **kwargs ) -> None:
		pass

	@abstractmethod
	def setup( self ) -> None:
		pass

	# define abstract properties

	@property
	@abstractmethod
	def base_path( self ) -> Path:
		"""
		Local base path where data for this service is persisted.

		:return: base path in the local file system
		"""
		pass

	@property
	@abstractmethod
	def base_url( self ) -> str:
		"""
		Base URL from where data for this service is fetched.

		:return: base url of this service
		"""
		pass

	@property
	@abstractmethod
	def logged_in( self ) -> bool:
		pass

	@property
	@abstractmethod
	def enabled( self ) -> bool:
		pass

	@property
	@abstractmethod
	def name( self ) -> str:
		pass

	@property
	@abstractmethod
	def display_name( self ) -> str:
		pass

class Handler( Protocol ):
	"""
	A handler defines the protocol for loading and saving documents, transforming them into a dict-like structure.
	Example: input can be a string, containing a GPX XML and the output is the parsed GPX structure.
	"""

	@abstractmethod
	def load( self, path: Optional[Path] = None, data: Optional[Union[str, bytes]] = None ) -> Union[Dict, Any]:
		"""
		Loads data either from the given path or the given string/byte array.

		:param path: path to load data from
		:param data: data to be used for transformation into a dict
		:return: loaded data (preferably a dict, but could also be any data structure)
		"""
		pass

	# noinspection PyMethodMayBeStatic
	def load_raw( self, path: Path ) -> Any:
		with open( path, encoding='utf-8', mode='r', buffering=8192 ) as p:
			return p.read()

	@abstractmethod
	def save( self, path: Path, data: Union[Dict, str, bytes] ) -> None:
		pass

	@abstractmethod
	def types( self ) -> List[str]:
		pass

class Importer( Protocol ):
	"""
	An importer is used to transform a (preferably) dict-like data structure into an activity or resource.
	"""

	@abstractmethod
	def load( self, data: Optional[Any] = None, path: Optional[Path] = None, url: Optional[str] = None, **kwargs ) -> Optional[Union[Activity, Resource]]:
		"""
		Loads data from a (remove) source as transforms this data into either an activity or at least into some kind of structured data.

		:param data: data to load from, either as str or bytes, this takes precedence over path and url
		:param path: local path to load data from, takes precedence over url parameter
		:param url: URL to load data from
		:param kwargs: additional parameters for implementers of this protocol
		:return: loaded data (an activity or structured data like dict)
		"""
		pass

	@property
	@abstractmethod
	def type( self ) -> str:
		"""
		Content type this importer supports.

		:return: content type
		"""
		pass

	@property
	@abstractmethod
	def activity_cls( self ) -> Optional[Type[Activity]]:
		"""
		Optional activity class this importer creates when loading resources.
		If this property is not None an activity will be returned when calling the load method.

		:return:
		"""
		pass

class Exporter( Protocol ):
	"""
	The opposite of an importer, used to transform an activity into a dict-like structure.
	"""

	@abstractmethod
	def save( self, data: Union[Dict, str, bytes], path: Optional[Path] = None, url: Optional[str] = None ) -> None:
		pass

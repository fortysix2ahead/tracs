
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Protocol
from typing import Union

from tracs.resources import Resource

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
	def path_for( self, activity: Activity = None, resource: Resource = None, ignore_overlay: bool = True ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.
		The returned path must point to a directory.

		:param activity: activity
		:param resource: resource
		:param ext: file extension for which the path should be returned, can be None
		:param ignore_overlay: flag to ignore overlay paths (if they exist)
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
	def setup( self, ctx ) -> None:
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


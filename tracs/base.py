
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union


@dataclass
class Resource:

	parent: Dict = field( default=None )
	name: str = field( default=None )
	type: str = field( default=None )
	status: int = field( default=100 )
	path: str = field( default=None )
	#path: Path = field( default=None )

	def __setattr__( self, name: str, value: Any ) -> None:
		super().__setattr__( name, value )
		if name != 'parent' and self.parent is not None:
			self.parent[name] = value

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

class Service( ABC ):
	"""
	Abstract base class for a service being able to consume activities from external sources.
	"""

	@abstractmethod
	def login( self ) -> bool:
		pass

	@abstractmethod
	def path_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path in the local file system where all artefacts of a provided activity are located.
		The returned path must point to a directory.

		:param a: activity
		:param ext: file extension for which the path should be returned, can be None
		:return: path of the activity in the local file system
		"""
		pass

	@abstractmethod
	def link_for( self, a: Activity, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the link path for an activity.

		:param a: activity to link
		:param ext: file extension
		:return: link path for activity
		"""
		pass

	@abstractmethod
	def fetch( self, force: bool ) -> [Activity]:
		pass

	@abstractmethod
	def download( self, activity: Activity, force: bool, pretend: bool ) -> None:
		pass

	@abstractmethod
	def link( self, activity: Activity, force: bool, pretend: bool ) -> None:
		pass

	@abstractmethod
	def setup( self ) -> None:
		pass

	# define abstract properties

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

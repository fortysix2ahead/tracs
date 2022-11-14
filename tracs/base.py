
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import List
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

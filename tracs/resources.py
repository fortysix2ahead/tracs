from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import InitVar
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from tracs.dataclasses import BaseDocument
from tracs.dataclasses import PERSIST
from tracs.dataclasses import PROTECTED

# todo: not sure if we still need the status
class ResourceStatus( Enum ):
	UNKNOWN = 100
	EXISTS = 200
	NO_CONTENT = 204
	NOT_FOUND = 404

# https://docs.python.org/3/library/dataclasses.html#descriptor-typed-fields
class ResourceDescriptor:

	def __get__( self, obj, type ):
		# getting a field value goes through this method
		pass

	def __set__( self, obj, value ):
		# value from __init__ in dataclass is passed to __set__
		pass

	def __delete__( self, instance ):
		pass

@dataclass
class Resource( BaseDocument ):
	name: str = field( default=None )
	type: str = field( default=None )
	path: str = field( default=None )
	source: str = field( default=None )
	status: int = field( default=None )
	summary: bool = field( default=False )
	uid: str = field( default=None )

	# additional field holding data of a resource, used when loading, but won't be persisted in db
	raw: Any = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # structured data making up this resource
	content: bytes = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # raw content as bytes
	text: InitVar[str] = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # decoded content as string, to be removed

	resources: List[Resource] = field( default_factory=list, repr=False, metadata={ PERSIST: False, PROTECTED: True } )

	def __post_init__( self, text: str ):
		super().__post_init__()
		self.content = text.encode( encoding='UTF-8' ) if text else self.content

	@property
	def classifier( self ) -> str:
		return self._uid()[0]

	@property
	def local_id( self ) -> int:
		return int( self._uid()[1] )

	@property  # property should be deprecated in favour of local id
	def raw_id( self ) -> int:
		return self.local_id

	def _uid( self ) -> Tuple[str, str]:
		classifier, raw_id = self.uid.split( ':', maxsplit=1 )
		return classifier, raw_id

	def as_text( self, encoding: str = 'UTF-8' ) -> Optional[str]:
		return self.content.decode( encoding )

	def summaries( self ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.summary), None )

	def recordings( self ) -> List[Resource]:
		return [r for r in self.resources if not r.summary]

@dataclass
class ResourceGroup:
	resources: List[Resource] = field( default_factory=list )

	def summary( self ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.summary), None )

	def recordings( self ) -> List[Resource]:
		return [r for r in self.resources if not r.summary]

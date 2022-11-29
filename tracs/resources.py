from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import InitVar
from enum import Enum
from re import compile
from re import Pattern
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from tracs.dataclasses import BaseDocument
from tracs.dataclasses import PERSIST
from tracs.dataclasses import PROTECTED

# todo: not sure if we still need the status
class ResourceStatus( Enum ):
	UNKNOWN = 100
	EXISTS = 200
	NO_CONTENT = 204
	NOT_FOUND = 404

pattern: Pattern = compile( '\w+\/(vnd\.(?P<vendor>\w+).)?((?P<subtype>\w+)\+)?(?P<suffix>\w+)' )

@dataclass
class ResourceType:

	# type/subtype
	# type "/" [tree "."] subtype ["+" suffix]* [";" parameter]

	type: str = field( default=None )
	subtype: str = field( default=None )
	suffix: str = field( default=None )
	vendor: str = field( default=None )

	activity_cls: Type = field( default=None )
	name: str = field( default=None )
	summary: bool = field( default=False )
	recording: bool = field( default=False )
	image: bool = field( default=False )

	def __post_init__( self ):
		if self.subtype or self.suffix or self.vendor:
			return
		if self.type and (m := pattern.match( self.type )):
			self.suffix = m.groupdict().get( 'suffix' )
			self.subtype = m.groupdict().get( 'subtype' )
			self.vendor = m.groupdict().get( 'vendor' )

	def extension( self ) -> Optional[str]:
		if self.suffix and self.subtype:
			return f'{self.subtype}' if not self.vendor else f'{self.subtype}.{self.suffix}'
		else:
			return self.suffix

@dataclass
class Resource( BaseDocument ):
	name: str = field( default=None )
	type: str = field( default=None )
	path: str = field( default=None )
	source: str = field( default=None )
	status: int = field( default=None, metadata={ PERSIST: False } )
	summary: bool = field( default=False, metadata={ PERSIST: False } )
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

	def get_child( self, resource_type: str ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.type == resource_type), None )

@dataclass
class ResourceGroup:
	resources: List[Resource] = field( default_factory=list )

	def summary( self ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.summary), None )

	def recordings( self ) -> List[Resource]:
		return [r for r in self.resources if not r.summary]

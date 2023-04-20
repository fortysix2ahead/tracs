from __future__ import annotations

from dataclasses import dataclass, field, Field, fields, InitVar
from enum import Enum
from re import compile, Pattern
from typing import Any, List, Optional, Tuple, Type

# todo: not sure if we still need the status
class ResourceStatus( Enum ):
	UNKNOWN = 100
	EXISTS = 200
	NO_CONTENT = 204
	NOT_FOUND = 404

pattern: Pattern = compile( '\w+\/(vnd\.(?P<vendor>\w+).)?((?P<subtype>\w+)\+)?(?P<suffix>\w+)' )
classifier_local_id_pattern = compile( '\w+\:\d+' )

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

	@property
	def other( self ) -> bool:
		return True if not self.summary and not self.recording and not self.image else False

@dataclass
class Resource:

	id: int = field( default=0 )

	name: Optional[str] = field( default=None )
	type: str = field( default=None )
	path: str = field( default=None )
	source: Optional[str] = field( default=None )
	status: int = field( default=None )
	summary: bool = field( default=False )
	uid: str = field( default=None )

	# additional fields holding data of a resource, used during load
	content: bytes = field( default=None, repr=False )  # raw content as bytes
	text: InitVar = field( default=None, repr=False )  # decoded content as string, can be used to initialize a resource from string
	raw: Any = field( default=None, repr=False ) # structured data making up this resource, will be converted from content
	# secondary field, companion to raw, might contain another form of structured data, i.e. a dataclass in parallel to a json
	data: Any = field( default=None, repr=False )

	# todo: remove later?
	resources: List[Resource] = field( default_factory=list, repr=False )

	__parent_activity__: List = field( default_factory=list, repr=False )

	# class methods

	@classmethod
	def fields( cls ) -> List[Field]:
		return list( fields( Resource ) )

	@classmethod
	def fieldnames( cls ) -> List[str]:
		return [f.name for f in fields( Resource )]

	def __post_init__( self, text: str ):
		self.content = text.encode( encoding='UTF-8' ) if text else self.content

	def __hash__( self ):
		return hash( (self.uid, self.path) )

	@property
	def parent_activity( self ) -> Any: # todo: would be nice to return Activity here ...
		return self.__parent_activity__

	@property
	def classifier( self ) -> str:
		return self._uid()[0]

	@property
	def local_id( self ) -> int:
		return int( self._uid()[1] )

	@property
	def local_id_str( self ) -> str:
		return self._uid()[1]

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

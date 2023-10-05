from __future__ import annotations

from dataclasses import dataclass, field, Field, fields, InitVar
from enum import Enum
from re import compile, Pattern
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import NAMESPACE_URL, uuid5

from dataclass_factory import Schema

from tracs.uid import UID

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

	id: int = field( default=None )

	name: Optional[str] = field( default=None )
	type: str = field( default=None )
	path: str = field( default=None )
	source: Optional[str] = field( default=None )
	status: int = field( default=None )
	summary: bool = field( default=False )
	uid: str = field( default=None )

	# additional fields holding data of a resource, used during load

	content: bytes = field( default=None, repr=False )
	"""Raw content as bytes"""
	text: InitVar = field( default=None, repr=False )
	"""Decoded content as string, can be used to initialize a resource from string"""
	raw: Any = field( default=None, repr=False )
	"""Structured data making up this resource, will be converted from content."""
	data: Any = field( default=None, repr=False )
	"""Secondary field as companion to raw, might contain another form of structured data, i.e. a dataclass in parallel to a json"""

	# todo: remove later?
	resources: List[Resource] = field( default_factory=list, repr=False )

	__parent_activity__: List = field( default_factory=list, repr=False )
	__uid__: UID = field( default=None, repr=False )

	def __post_init__( self, text: str ):
		self.__uid__ = UID( f'{self.uid}?{self.path}' ) if self.uid and self.path else None
		self.content = text.encode( encoding='UTF-8' ) if text else self.content

	def __hash__( self ):
		return hash( (self.uid, self.path) )

	# class methods

	@classmethod
	def fields( cls ) -> List[Field]:
		return list( fields( Resource ) )

	@classmethod
	def fieldnames( cls ) -> List[str]:
		return [f.name for f in fields( Resource )]

	@classmethod
	def schema( cls ) -> Schema:
		return Schema(
			exclude=['content', 'data', 'raw', 'resources', 'status', 'summary', 'text'],
			omit_default=True,
			skip_internal=True,
			unknown='unknown',
		)

	# additional properties

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

	@property
	def uidpath( self ) -> str:
		return self.__uid__.uid

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
class Resources:
	"""
	Dict-like container for resources.
	"""

	data: Dict[str, Resource] = field( default_factory=dict )

	# magic methods

	def __len__( self ) -> int:
		return len( self.data )

	# add/remove etc.

	def add( self, *resources: Resource ):
		for r in resources:
			uuid = str( uuid5( NAMESPACE_URL, f'{r.uid}/{r.path}' ) )
			if uuid in self.data.keys():
				raise KeyError( f'resource with UUID {uuid} already contained in resources' )
			else:
				r.id = _next_id( self.data )
				self.data[uuid] = r

@dataclass
class ResourceGroup:
	resources: List[Resource] = field( default_factory=list )

	def summary( self ) -> Optional[Resource]:
		return next( (r for r in self.resources if r.summary), None )

	def recordings( self ) -> List[Resource]:
		return [r for r in self.resources if not r.summary]

def _next_id( d: Dict[str, Resource] ) -> int:
	existing_ids = [r.id for r in d.values()]
	id_range = range( 1, max( existing_ids ) + 2 ) if len( existing_ids ) > 0 else [1]
	return set( id_range ).difference( set( existing_ids ) ).pop()

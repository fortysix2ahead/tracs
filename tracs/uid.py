from __future__ import annotations

from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse, urlunsplit

from attrs import define, field
from fs.path import basename, frombase, parts

@define( eq=False, order=False, repr=False )
class UID:

	classifier: str = field( default=None )
	"""Classifier is equal to the url scheme. Example: uid = polar:101, classifier = polar."""

	local_id: int = field( default=None )
	"""Identifier of an activity, equal to the URI path. Example: uid = polar:101, local_id = 101."""

	path: Optional[str] = field( default=None )
	"""Path of a resource of an activity. Example: uid = polar:101?recording.gpx, path = recording.gpx."""

	part: Optional[int] = field( default=None )
	"""Part number of an activity. Example: uid = polar:101#2, part = 2."""

	@classmethod
	def of( cls, uid: UID|str, path: Optional[str] = None ) -> UID:
		return from_str( uid, path ) if isinstance( uid, str ) else uid

	@classmethod
	def from_str( cls, uid: str ) -> UID:
		return cls.of( uid, None )

	@classmethod
	def from_strs( cls, uids: List[str] ) -> List[UID]:
		return [ cls.of( u, None ) for u in uids ]

	def __eq__( self, other ):
		return self.uid == other.uid if isinstance( other, UID ) else self.uid == other

	def __hash__( self ) -> int:
		return hash( self.uid )

	def __lt__( self, other ):
		return self.uid < other.uid if isinstance( other, UID ) else self.uid < other

	def __gt__( self, other ):
		return self.uid > other.uid if isinstance( other, UID ) else self.uid > other

	def __str__( self ) -> str:
		return self.uid

	def __repr__( self ) -> str:
		return self.__str__()

	@property
	def uid( self ):
		return self.as_str

	@property
	def head( self ) -> str:
		return f'{self.classifier}:{self.local_id}' if self.local_id else self.classifier

	@property
	def tail( self ) -> Optional[str]:
		if self.path and self.part:
			return f'{self.path}#{self.part}'
		elif self.path:
			return self.path
		elif self.part:
			return str( self.part )
		else:
			return None

	@property
	def base( self ) -> UID:
		return UID( classifier=self.classifier, local_id=self.local_id, path=basename( self.path ), part=self.part )

	def resolve( self, fn: Callable ) -> UID:
		return UID( classifier=self.classifier, local_id=self.local_id, path=fn( self.local_id, basename( self.path ) ), part=self.part )

	@property
	def as_str( self ) -> str:
		return to_str( self )

	@property
	def as_tuple( self ) -> Tuple[str, int]:
		return self.classifier, self.local_id

	@property
	def as_tuple_str( self ) -> str:
		return f'{self.classifier}:{self.local_id}' if self.local_id else self.classifier

	@property
	def as_triple( self ) -> Tuple[str, int, str]:
		return self.classifier, self.local_id, self.path

	def denotes_service( self, service_names: List[str] = None ) -> bool:
		is_service = True if self.classifier and not self.local_id and not self.path else False
		if service_names:
			return is_service if self.classifier in service_names else False
		else:
			return is_service

	def denotes_activity( self ) -> bool:
		return True if self.classifier and self.local_id and not self.path else False

	def denotes_resource( self ) -> bool:
		return True if self.classifier and self.local_id and self.path else False

	def denotes_part( self ) -> bool:
		return True if self.classifier and self.local_id and self.part else False

# convenience ...

def uid( u: UID|str ) -> UID:
	return from_str( u, None ) if isinstance( u, str ) else u

def uids( *s: str ) -> List[UID]:
	return [ from_str( u, None ) for u in s ]

# serialization

def from_str( uid: str, path: str = None ) -> UID:
	pr = urlparse( uid )

	# interpret a URI without a colon as scheme instead of path
	if pr.path and not pr.scheme:
		classifier, local_id = pr.path, None

	else:
		classifier = pr.scheme
		match len( _parts := parts( pr.path ) ):
			case 1:
				local_id = None
			case 2:
				local_id = _parts[1]
			case 3:
				local_id, path = _parts[1], _parts[2] if not path else path
			case _:
				local_id, path = _parts[1], frombase( _parts[1], pr.path )[1:]

	try:
		local_id = int( local_id )
	except (TypeError, ValueError):
		local_id = None

	try:
		part = int( pr.fragment )
	except (TypeError, ValueError):
		part = None

	return UID( classifier=classifier, local_id=local_id, path=path, part=part )

def to_str( uid: UID ) -> Optional[str]:
	if uid is None:
		return None

	if not isinstance( uid, UID ):
		raise ValueError()

	if uid.classifier and not uid.local_id:
		return urlunsplit( ['', '', uid.classifier, uid.path or '', uid.part or ''] )
	else:
		local_id = str( uid.local_id ) if uid.local_id else ''
		path = f'{local_id}/{uid.path}' if uid.path else local_id
		part = str( uid.part ) if uid.part else ''
		return urlunsplit( [uid.classifier, '', path, '', part] )

# hooks for cattrs

def uid_to_str( uid: UID ) -> str:
	return to_str( uid )

def str_to_uid( data: str, cls: type ) -> UID:
	return from_str( data )

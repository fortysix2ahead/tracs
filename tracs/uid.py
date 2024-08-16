from __future__ import annotations

from typing import ClassVar, List, Optional, Tuple
from urllib.parse import ParseResult, SplitResult, urlparse, urlsplit, urlunsplit

from attrs import define, field
from cattrs import Converter, GenConverter

@define( order=False )
class UID:

	converter: ClassVar[Converter] = GenConverter()

	uid: str = field( default=None )
	"""Contains the full uid string. Example: polar:101?recording.gpx"""
	classifier: str = field( default=None )
	"""Classifier is equal to the url scheme. Example: uid = polar:101, classifier = polar."""
	local_id: int = field( default=None )
	"""Identifier of an activity, equal to the path. Example: uid = polar:101, local_id = 101."""
	path: str = field( default=None )
	"""Path of a resource of an activity. Example: uid = polar:101?recording.gpx, path = recording.gpx."""
	part: int = field( default=None )
	"""Part number of an activity. Example: uid = polar:101#2, part = 2."""

	def __attrs_post_init__( self ):
		if self.uid:
			classifier, local_id, path, part = self._uidparse( self.uid )
			# allow overwrting path
			path = self.path if self.path else path
			# set attributes and update uid
			self.classifier, self.local_id, self.path, self.part = classifier, local_id, path, part
			self.uid = self._unsplit( classifier, local_id, path, part )
		else:
			self.uid = self._unsplit( self.classifier, self.local_id, self.path, self.part )

	# todo: this can be removed as the minimum python version is now 3.10
	# custom url parsing to overcome inconsistencies between python 3.8 and 3.9+:
	# url       python 3.8    python 3.9+ (in format scheme,path)
	# polar    ,polar         ,polar
	# polar:   polar,         polar,
	# polar:1  ,polar:1      polar,1
	# noinspection PyMethodMayBeStatic
	def _urlparse( self, url: str ) -> ParseResult:
		url: ParseResult = urlparse( url )
		if not url.scheme and url.path:
			if ':' in url.path:
				path, local_id = url.path.split( ':' )
				return ParseResult( scheme=path, netloc=url.netloc, path=local_id, params=url.params, query=url.query, fragment=url.fragment )
			else:
				return ParseResult( scheme=url.path, netloc=url.netloc, path='', params=url.params, query=url.query, fragment=url.fragment )
		else:
			return url

	# noinspection PyMethodMayBeStatic
	def _urlsplit( self, url: str ) -> SplitResult:
		url: SplitResult = urlsplit( url )
		if not url.scheme and url.path:
			if ':' in url.path:
				path, local_id = url.path.split( ':' )
				return SplitResult( scheme=path, netloc=url.netloc, path=local_id, query=url.query, fragment=url.fragment )
			else:
				return SplitResult( scheme=url.path, netloc=url.netloc, path='', query=url.query, fragment=url.fragment )
		else:
			return url

	def _uidparse( self, url: str  ) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
		url: SplitResult = self._urlsplit( url )
		classifier = url.scheme if url.scheme else None
		path_split = url.path.split( '/', maxsplit=1 )
		local_id = int( path_split[0] ) if path_split[0] else None
		path = path_split[1] if len( path_split ) > 1 else None
		part = int( url.fragment ) if url.fragment else None
		return classifier, local_id, path, part

	# noinspection PyMethodMayBeStatic
	def _unsplit( self, classifier, local_id, path, part ) -> str:
		if classifier and not local_id:
			return urlunsplit( ['', '', classifier if classifier else '', path if path else '', part if part else ''] )
		else:
			p = f'{local_id if local_id else ""}'
			p = f'{p}/{path}' if path else p
			return urlunsplit( [classifier if classifier else '', '', p, '', str( part ) if part else ''] )

	def __hash__( self ) -> int:
		return hash( self.uid )

	def __lt__( self, other: UID ):
		return self.uid < other.uid

	def __str__( self ) -> str:
		return self.uid

	# todo: rename, clspath is not a good name
	@property
	def clspath( self ) -> str:
		return f'{self.classifier}:{self.local_id}' if self.local_id else self.classifier

	@property
	def as_tuple( self ) -> Tuple[str, int]:
		return self.classifier, self.local_id

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

	# serialization

	def to_str( self ):
		return UID.converter.unstructure( self )

	@classmethod
	def from_str( cls, obj: str ) -> UID:
		return UID.converter.structure( obj, UID )

# setup converter

UID.converter.register_unstructure_hook( UID, lambda u: str( u ) )
UID.converter.register_structure_hook( UID, lambda u, v: UID( uid=u ) )

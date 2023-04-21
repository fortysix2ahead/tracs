from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import ParseResult
from urllib.parse import urlparse, urlunparse

@dataclass
class UID:

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

	def __post_init__( self ):
		if self.uid:
			self.classifier, self.local_id, self.path, self.part = self._uidparse( self.uid )
		else:
			self.uid = self._unparse( self.classifier, self.local_id, self.path, self.part )

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

	def _uidparse( self, url: str  ) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
		url: ParseResult = self._urlparse( url )
		return self._uidfields( url.scheme, url.path, url.query, url.fragment )

	# noinspection PyMethodMayBeStatic
	def _uidfields( self, scheme, path, query, fragment ) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
		classifier = scheme if scheme else None
		local_id = int( path ) if path else None
		path = query if query else None
		part = int( fragment ) if fragment else None
		return classifier, local_id, path, part

	# noinspection PyMethodMayBeStatic
	def _unparse( self, classifier, local_id, path, part ) -> str:
		if classifier and not local_id:
			return urlunparse( ['', '', classifier if classifier else '', '', path if path else '', part if part else ''] )
		else:
			return urlunparse( [classifier if classifier else '', '', str( local_id ) if local_id else '', '', path if path else '', str( part ) if part else ''] )

	def __hash__( self ) -> int:
		return hash( self.uid )

	def __lt__( self, other: UID ):
		return self.uid < other.uid

	def __str__( self ) -> str:
		return self.uid

	@property
	def clspath( self ) -> str:
		return f'{self.classifier}:{self.local_id}'

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
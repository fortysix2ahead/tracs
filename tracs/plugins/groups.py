
from typing import List

from attrs import define
from attrs import field
from attrs import Attribute
from logging import getLogger
from rich.console import Console

from . import document
from ..activity import Activity
from ..activity import ActivityRef
from ..dataclasses import PERSIST
from ..dataclasses import PROTECTED

log = getLogger( __name__ )
console = Console()

def str2groups( v ) -> List:
	rval = []
	if v and isinstance( v, dict ):
		for id, uid in zip( v.get( 'ids' ), v.get( 'uids' ) ):
			rval.append( ActivityRef( id=id, uid=uid ) )
	elif v and isinstance( v, list ):
		rval = v
	return rval

@document
@define
class ActivityGroup( Activity ):

	group: List[Activity] = field( init=True, default=[], metadata={ PERSIST: False, PROTECTED: True } )
	group_ids: List[int] = field( init=True, default=[], metadata={ PROTECTED: True } )
	group_uids: List[str] = field( init=True, default=[], metadata={ PROTECTED: True } )
	group_classifiers: List[str] = field( init=False, default=[], metadata={ PERSIST: False } )
	group_refs: List[ActivityRef] = field( init=True, default=[], converter=str2groups, metadata={ PERSIST: False } ) # not sure if we really need this field
	classifiers: List[str] = field( init=False, default=[], metadata={ PERSIST: False } )

	def __post_init__( self ):
		super().__post_init__()

		self.raw_id = self.id
		self.classifier = 'group'
		self.uid = f'{self.classifier}:{self.raw_id}'

		if self.group:
			if all( isinstance( g, Activity ) for g in self.group ):
				self.group_ids = [a.doc_id for a in self.group]
				self.group_uids = [a.uid for a in self.group]
				self.group_classifiers = [uid.split( ':' )[0] for uid in self.group_uids]
				self.classifiers = sorted( list( set( self.group_classifiers ) ) )
				# self.group_refs = [ActivityRef( id, uid ) for id, uid in zip( self.group_ids, self.group_uids )]

				derived_atts = {}

				for a in self.group:
					if hasattr( a.__class__, '__attrs_attrs__' ):
						atts: List[Attribute] = a.__class__.__attrs_attrs__
						for att in atts:
							if att.name not in derived_atts.keys():
								if not att.metadata.get( PROTECTED, False ) and (value := getattr( a, att.name )):
									derived_atts[att.name] = value

				for key, value in derived_atts.items():
					setattr( self, key, value )

			# elif all( isinstance( g, ActivityRef ) for g in self.groups ):
			# 	self.group_ids = [g.id for g in self.groups]
			# 	self.group_uids = [g.uid for g in self.groups]
			# 	self.group_classifiers = [uid.split( ':' )[0] for uid in self.group_uids]
			# 	self.classifiers = sorted( list( set( self.group_classifiers ) ) )
			# 	self.group_refs = [ActivityRef( id, uid ) for id, uid in zip( self.group_ids, self.group_uids )]

			# elif isinstance( self.group, list ):
			# 	self.group_ids = self.group.get( 'ids' )
			# 	self.group_uids = self.groups.get( 'uids' )
			# 	self.group_classifiers = [uid.split( ':' )[0] for uid in self.group_uids]
			# 	self.classifiers = sorted( list( set( self.group_classifiers ) ) )
			# 	self.group_refs = [ActivityRef( id, uid ) for id, uid in zip( self.group_ids, self.group_uids )]

	def group_classifiers_str( self ) -> str:
		return ','.join( sorted( list( set( self.group_classifiers ) ) ) )

#	@property
#	def groups( self ) -> Mapping:
#		return self._access_map( KEY_GROUPS )

	# @property
	# def group_for( self ) -> List[int]:
	# 	return self.groups.get( 'ids', [] )
	#
	# @property
	# def group_for_uid( self ) -> List[str]:
	# 	return self.groups.get( 'uids', [] )
	#
	# @property
	# def grouped_by( self ) -> Optional[int]:
	# 	return self.groups.get( 'parent', None )
	#
	# def _access_map( self, key: str ) -> Dict:
	# 	if not self.__contains__( key ) or not self.__getitem__( key ):
	# 		self.__setitem__( key, { } )
	# 	return self.__getitem__( key )

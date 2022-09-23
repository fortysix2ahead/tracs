
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Tuple
from typing import Union

from logging import getLogger
from typing import List
from typing import Optional

from .activity_types import ActivityTypes
from .dataclasses import BaseDocument
from .dataclasses import PERSIST
from .dataclasses import PROTECTED

log = getLogger( __name__ )

# noinspection PyTypeChecker
def str2activitytype( v: Union[ActivityTypes, str] ) -> ActivityTypes:
	if type( v ) is ActivityTypes:
		return v
	elif type( v ) is str:
		return ActivityTypes.get( v )
	else:
		return None

@dataclass
class Resource( BaseDocument ):

	name: str = field( default=None )
	type: str = field( default=None )
	path: str = field( default=None )
	source: str = field( default=None )
	status: int = field( default=None )
	summary: bool = field( default=False )
	uid: str = field( default=None )

	raw: Any = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # structured raw data making up this resource
	raw_data: Union[str, bytes] = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # serialized version of raw, can be str or bytes

	# fields are not yet used, but shall replace raw_data in the future, following the fields of requests.response
	content: bytes = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # raw content, as bytes
	text: str = field( default=None, repr=False, metadata={ PERSIST: False, PROTECTED: True } )  # decoded content as string

	def classifier( self ):
		return self._uid()[0]

	def raw_id( self ):
		return self._uid()[1]

	def _uid( self ) -> Tuple[str, str]:
		classifier, raw_id = self.uid.split( ':', maxsplit=1 )
		return classifier, raw_id

@dataclass
class ResourceGroup:

	resources: List[Resource] = field( default_factory=list )

	def summary( self ) -> Optional[Resource]:
		return next( ( r for r in self.resources if r.summary ), None )

	def recordings( self ) -> List[Resource]:
		return [ r for r in self.resources if not r.summary ]

@dataclass
class ActivityRef:

	id: str = field( default=None )
	uid: str = field( default=None )

	classifier: str = field( init=False, default=None )
	raw_id: str = field( init=False, default=None )

	def __post_init__( self ):
		self.classifier, self.raw_id = self.uid.split( ':' ) if self.uid else (None, None)

@dataclass
class Activity( BaseDocument ):

	classifier: str = field( default=None, metadata={ PROTECTED: True } ) # classifier of this activity, only used in subclasses
	uid: str = field( default=None, metadata={ PROTECTED: True } ) # unique id of this actvity in the form of <classifier:number>, only used in subclasses
	uids: List[str] = field( default_factory=list, metadata={ PROTECTED: True } ) # uids of activities which belong to this activity

	raw: Any = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # structured raw data used for initialization from external data
	raw_id: int = field( default=None, metadata= { PROTECTED: True } )  # raw id as raw data might not contain all data necessary
	raw_name: str = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # same as raw id
	raw_data: Union[str, bytes] = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # serialized version of raw, can be i.e. str or bytes

	# local_id: int = field( default=None, metadata= { PROTECTED: True } )  # same as raw_id

	name: str = field( default=None ) # activity name
	type: ActivityTypes = field( default=None ) # activity type
	description: str = field( default=None ) # description
	tags: List[str] = field( default_factory=list ) # list of tags
	location_country: str = field( default=None ) #
	location_state: str = field( default=None ) #
	location_city: str = field( default=None ) #
	location_place: str = field( default=None ) #
	route: str = field( default=None ) #

	time: datetime = field( default=None ) # activity time (UTC)
	localtime: datetime = field( default=None ) # activity time (local)
	timezone: str = field( default=None ) #
	duration: time = field( default=None ) #
	duration_moving: time = field( default=None ) #

	distance: float = field( default=None ) #
	ascent: float = field( default=None ) #
	descent: float = field( default=None ) #
	elevation_max: float = field( default=None ) #
	elevation_min: float = field( default=None ) #
	speed: float = field( default=None ) #
	speed_max: float = field( default=None ) #

	heartrate: float = field( default=None ) #
	heartrate_max: float = field( default=None ) #
	heartrate_min: float = field( default=None ) #
	calories: float = field( default=None ) #

	metadata: Dict = field( init=False, default_factory=dict, metadata={ PROTECTED: True, PERSIST: False } )
	resources: List[Resource] = field( init=True, default_factory=list, metadata={ PROTECTED: True, PERSIST: False } )

	#parent: Activity = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )
	#parent_ref: ActivityRef = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )
	#parent_id: int = field( default=None, metadata={ PROTECTED: True } )
	#parent_uid: str = field( default=None, metadata={ PROTECTED: True } )

	#is_group: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility
	#is_multipart: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility

	def __post_init__( self ):
		super().__post_init__()

		if self.raw:
			self.__raw_init__( self.raw )

	def __raw_init__( self, raw: Any ) -> None:
		"""
		Called from __post_init__ with raw data as parameter and can be overridden in subclasses. Will not be called when raw is None.
		:return:
		"""
		pass

		#if len( self.resources ) > 0 and all( type( r ) is dict for r in self.resources ):
		#	self.resources = [ Resource( **r ) for r in self.resources ]

	def init_from( self, other: Activity = None, raw: Dict = None, force: bool = False ) -> Activity:
		"""
		Initializes this activity with data from another activity/dictionary.

		:param other: other activity
		:param raw: raw data
		:param force: flag to overwrite existing data from other, regardless of existing values (otherwise non-null values will be preferred
		:return: self, for convenience
		"""
		if other:
			for f in fields( self ):
				if not f.metadata.get( PROTECTED, False ):
					other_value = getattr( other, f.name )
					if force:
						setattr( self, f.name, other_value )
					else:
						new_value = getattr( self, f.name ) or other_value
						setattr( self, f.name, new_value )
		elif raw:
			self.raw = raw
			self.__post_init__()

		return self
	
	def resource_group( self ) -> ResourceGroup:
		return ResourceGroup( resources=self.resources )

@dataclass
class MultipartActivity( Activity ):

	parts: List[Activity] = field( default_factory=list, metadata={ 'persist_as': '_parts' } )

#	@property
#	def parts( self ) -> Mapping:
#		return self._access_map( KEY_PARTS )

	@property
	def part_for( self ) -> List[int]:
		return self.parts.get( 'ids', [] )

	@property
	def part_of( self ) -> Optional[int]:
		return self.parts.get( 'parent', None )


from __future__ import annotations

from datetime import datetime
from typing import Dict
from typing import Union

from attrs import define
from attrs import field
from logging import getLogger
from typing import List
from typing import Optional

from .activity_types import ActivityTypes
from .dataclasses import BaseDocument
from .dataclasses import PERSIST
from .dataclasses import PROTECTED
from .dataclasses import str2datetime
from .dataclasses import str2time

log = getLogger( __name__ )

# noinspection PyTypeChecker
def str2activitytype( v: Union[ActivityTypes, str] ) -> ActivityTypes:
	if type( v ) is ActivityTypes:
		return v
	elif type( v ) is str:
		return ActivityTypes.get( v )
	else:
		return None

@define
class Resource:

	name: str = field( init=True, default=None )
	type: str = field( init=True, default=None )
	path: str = field( init=True, default=None )
	status: int = field( init=True, default=None )

@define
class ActivityRef:

	id: str = field( init=True, default=None )
	uid: str = field( init=True, default=None )

	classifier: str = field( init=False, default=None )
	raw_id: str = field( init=False, default=None )

	def __attrs_post_init__( self ):
		self.classifier, self.raw_id = self.uid.split( ':' ) if self.uid else (None, None)

@define( init=True )
class Activity( BaseDocument ):

	name: str = field( init=True, default=None ) # activity name
	type: ActivityTypes = field( init=True, default=None, converter=str2activitytype ) # activity type
	description: str = field( init=True, default=None ) # description
	tags: List[str] = field( init=True, default=[] ) # list of tags
	location_country: str = field( init=True, default=None ) #
	location_state: str = field( init=True, default=None ) #
	location_city: str = field( init=True, default=None ) #
	location_place: str = field( init=True, default=None ) #
	route: str = field( init=True, default=None ) #

	time: datetime = field( init=True, default=None, converter=str2datetime ) # activity time (UTC)
	localtime: datetime = field( init=True, default=None, converter=str2datetime ) # activity time (local)
	timezone: str = field( init=True, default=None ) #
	duration: time = field( init=True, default=None, converter=str2time ) #
	duration_moving: time = field( init=True, default=None, converter=str2time ) #

	distance: float = field( init=True, default=None ) #
	ascent: float = field( init=True, default=None ) #
	descent: float = field( init=True, default=None ) #
	elevation_max: float = field( init=True, default=None ) #
	elevation_min: float = field( init=True, default=None ) #
	speed: float = field( init=True, default=None ) #
	speed_max: float = field( init=True, default=None ) #

	heartrate: float = field( init=True, default=None ) #
	heartrate_max: float = field( init=True, default=None ) #
	heartrate_min: float = field( init=True, default=None ) #
	calories: float = field( init=True, default=None ) #

	groups: Dict = field( init=True, default={}, metadata={ PROTECTED: True } ) # todo: for backward compatibility
	metadata: Dict = field( init=True, default={}, metadata={ PROTECTED: True } )
	resources: List[Resource] = field( init=True, default=[], metadata={ PROTECTED: True } )

	parent: Activity = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	parent_ref: ActivityRef = field( init=True, default=None, metadata={ PERSIST: False, PROTECTED: True } )
	parent_id: int = field( init=True, default=None, metadata={ PROTECTED: True } )
	parent_uid: str = field( init=True, default=None, metadata={ PROTECTED: True } )

	is_group: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility
	is_multipart: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility

	def __attrs_post_init__( self ):
		super().__attrs_post_init__()

		# todo: for backward compatibility
		if isinstance( self.groups, dict ) and 'parent' in self.groups:
			self.parent_id = self.groups['parent']
			self.parent_uid = f"group:{self.groups['parent']}"
			self.parent_ref = ActivityRef( self.parent_id, self.parent_uid )

		if len( self.resources ) > 0 and all( lambda r: type( r ) is dict for r in self.resources ):
			self.resources = [ Resource( **r ) for r in self.resources ]

class MultipartActivity( Activity ):

	parts: List[Activity] = field( init=True, default=[], metadata={ 'persist_as': '_parts' } )

#	@property
#	def parts( self ) -> Mapping:
#		return self._access_map( KEY_PARTS )

	@property
	def part_for( self ) -> List[int]:
		return self.parts.get( 'ids', [] )

	@property
	def part_of( self ) -> Optional[int]:
		return self.parts.get( 'parent', None )


from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import Field
from dataclasses import fields
from datetime import datetime
from datetime import time
from typing import Any
from typing import Dict
from typing import Union

from logging import getLogger
from typing import List
from typing import Optional

from tzlocal import get_localzone_name

from .activity_types import ActivityTypes
from .dataclasses import BaseDocument
from .dataclasses import FILTERABLE
from .dataclasses import FILTER_ALIAS
from .dataclasses import PERSIST
from .dataclasses import PROTECTED
from .resources import Resource
from .resources import ResourceGroup

log = getLogger( __name__ )

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

	classifier: str = field( default=None, metadata={ PROTECTED: True, FILTERABLE: True, FILTER_ALIAS: [ 'service', 'source' ] } ) # classifier of this activity, only used in subclasses
	uid: str = field( default=None, metadata={ PROTECTED: True, FILTERABLE: True } ) # unique id of this activity in the form of <classifier:number>, only used in subclasses
	uids: List[str] = field( default_factory=list, metadata={ PROTECTED: True, FILTERABLE: True } ) # uids of activities which belong to this activity

	raw: Any = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # structured raw data used for initialization from external data
	raw_id: int = field( default=None, metadata= { PROTECTED: True, FILTERABLE: True } )  # raw id as raw data might not contain all data necessary
	raw_name: str = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # same as raw id
	raw_data: Union[str, bytes] = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )  # serialized version of raw, can be i.e. str or bytes

	local_id: int = field( default=None, metadata= { PROTECTED: True, FILTERABLE: True } )  # same as raw_id

	name: str = field( default=None, metadata={ FILTERABLE: True } ) # activity name
	type: ActivityTypes = field( default=None, metadata={ FILTERABLE: True } ) # activity type
	description: str = field( default=None, metadata={ FILTERABLE: True } ) # description
	tags: List[str] = field( default_factory=list, metadata={ FILTERABLE: True } ) # list of tags
	equipment: List[str] = field( default_factory=list, metadata={ FILTERABLE: True } ) # list of equipment tags
	location_country: str = field( default=None, metadata={ FILTERABLE: True, FILTER_ALIAS: [ 'country' ] } ) #
	location_state: str = field( default=None, metadata={ FILTERABLE: True, FILTER_ALIAS: [ 'state' ] } ) #
	location_city: str = field( default=None, metadata={ FILTERABLE: True, FILTER_ALIAS: [ 'city' ] } ) #
	location_place: str = field( default=None, metadata={ FILTERABLE: True, FILTER_ALIAS: [ 'place' ] } ) #
	location_latitude_start: float = field( default=None, metadata={ FILTERABLE: True } ) #
	location_longitude_start: float = field( default=None, metadata={ FILTERABLE: True } ) #
	location_latitude_end: float = field( default=None, metadata={ FILTERABLE: True } ) #
	location_longitude_end: float = field( default=None, metadata={ FILTERABLE: True } ) #
	route: str = field( default=None, metadata={ FILTERABLE: True } ) #

	time: datetime = field( default=None, metadata={ FILTERABLE: True, FILTER_ALIAS: [ 'date', 'datetime' ] } ) # activity time (UTC)
	time_end: datetime = field( default=None, metadata={ FILTERABLE: True } ) # activity end time (UTC)
	localtime: datetime = field( default=None, metadata={ FILTERABLE: True } ) # activity time (local)
	localtime_end: datetime = field( default=None, metadata={ FILTERABLE: True } ) # activity end time (local)
	timezone: str = field( default=get_localzone_name(), metadata={ FILTERABLE: True } ) # timezone of the activity, local timezone by default
	duration: time = field( default=None, metadata={ FILTERABLE: True } ) #
	duration_moving: time = field( default=None, metadata={ FILTERABLE: True } ) #

	distance: float = field( default=None, metadata={ FILTERABLE: True } ) #
	ascent: float = field( default=None, metadata={ FILTERABLE: True } ) #
	descent: float = field( default=None, metadata={ FILTERABLE: True } ) #
	elevation_max: float = field( default=None, metadata={ FILTERABLE: True } ) #
	elevation_min: float = field( default=None, metadata={ FILTERABLE: True } ) #
	speed: float = field( default=None, metadata={ FILTERABLE: True } ) #
	speed_max: float = field( default=None, metadata={ FILTERABLE: True } ) #

	heartrate: float = field( default=None, metadata={ FILTERABLE: True } ) #
	heartrate_max: float = field( default=None, metadata={ FILTERABLE: True } ) #
	heartrate_min: float = field( default=None, metadata={ FILTERABLE: True } ) #
	calories: float = field( default=None, metadata={ FILTERABLE: True } ) #

	metadata: Dict = field( init=False, default_factory=dict, metadata={ PROTECTED: True, PERSIST: False } )
	resources: List[Resource] = field( init=True, default_factory=list, metadata={ PROTECTED: True, PERSIST: False } )

	#parent: Activity = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )
	#parent_ref: ActivityRef = field( default=None, metadata={ PERSIST: False, PROTECTED: True } )
	#parent_id: int = field( default=None, metadata={ PROTECTED: True } )
	#parent_uid: str = field( default=None, metadata={ PROTECTED: True } )

	#is_group: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility
	#is_multipart: bool = field( init=False, default=False, metadata={ PERSIST: False } ) # todo: for backward compatibility

	@property
	def abbreviated_type( self ) -> str:
		return self.type.abbreviation if self.type else ':question_mark:'

	def __post_init__( self, serialized_data: Optional[Dict] ):
		super().__post_init__( serialized_data=serialized_data )

		if self.raw:
			self.__raw_init__( self.raw )

	def __unserialize__( self, f: Field, v: Any ) -> Any:
		if f.name == 'type':
			return ActivityTypes.get( v )
		elif f.name in [ 'time', 'time_end', 'localtime', 'localtime_end' ]:
			return datetime.fromisoformat( v )
		elif f.name in [ 'duration', 'duraton_moving' ]:
			return time.fromisoformat( v )
		else:
			return v

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
			self.__post_init__( serialized_data=None )

		return self

	def tag( self, tag: str ):
		if tag not in self.tags:
			self.tags.append( tag )
			self.tags = sorted( self.tags )

	def untag( self, tag: str ):
		self.tags.remove( tag )

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

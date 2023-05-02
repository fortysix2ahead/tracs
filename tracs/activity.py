
from __future__ import annotations

from dataclasses import dataclass, field, Field, fields, InitVar, MISSING, replace
from datetime import datetime, time, timedelta
from logging import getLogger
from typing import Any, Callable, ClassVar, Dict, List, Optional, TypeVar

from dataclass_factory import Schema
from tzlocal import get_localzone_name

from tracs.activity_types import ActivityTypes
from tracs.resources import Resource
from tracs.uid import UID
from tracs.utils import sum_times, unique_sorted

log = getLogger( __name__ )

T = TypeVar('T')

PROTECTED_FIELDS = [ 'id' ]

@dataclass
class Fields:

	__resolvers__: ClassVar[Dict[str, Callable]] = field( default={} )

	def __getattribute__( self, name: str ) -> Any:
		if name in Fields.__resolvers__.keys():
			return Fields.__resolvers__[name]()
		else:
			return super().__getattribute__( name )

@dataclass( eq=True )
class ActivityPart:

	gap: time = field( default=None )
	uids: List[str] = field( default_factory=list )

	__uids__: List[UID] = field( default_factory=list )

	def __post_init__(self):
		self.__uids__ = [UID( uid ) for uid in self.uids]

	@classmethod
	def schema( cls ) -> Schema:
		return Schema( omit_default=True, skip_internal=True, unknown='unknown' )

	@property
	def classifiers( self ) -> List[str]:
		return unique_sorted( [ uid.classifier for uid in self.__uids__ ] )

	@property
	def activity_uids( self ) -> List[str]:
		return [ uid.uid for uid in self.as_activity_uids ]

	@property
	def as_uids( self ) -> List[UID]:
		return unique_sorted( self.__uids__ )

	@property
	def as_activity_uids( self ) -> List[UID]:
		return unique_sorted( [ UID( classifier=uid.classifier, local_id=uid.local_id ) for uid in self.__uids__ ] )

@dataclass( eq=True ) # todo: mark fields with proper eq attributes
class Activity:

	id: int = field( default=None )
	"""Integer id of this activity, same as key used in dictionary which holds activities, will not be persisted"""
	uids: List[str] = field( default_factory=list )
	"""List of uids of resources which belong to this activity"""

	name: Optional[str] = field( default=None )
	"""activity name"""
	type: Optional[ActivityTypes] = field( default=None )
	"""activity type"""
	description: str = field( default=None )
	"""description"""
	tags: List[str] = field( default_factory=list )
	"""list of tags"""
	equipment: List[str] = field( default_factory=list )
	"""list of equipment tags"""

	location_country: Optional[str] = field( default=None ) #
	location_state: Optional[str] = field( default=None ) #
	location_city: Optional[str] = field( default=None ) #
	location_place: Optional[str] = field( default=None ) #
	location_latitude_start: float = field( default=None ) #
	location_longitude_start: float = field( default=None ) #
	location_latitude_end: float = field( default=None ) #
	location_longitude_end: float = field( default=None ) #
	route: str = field( default=None ) #

	time: datetime = field( default=None )
	"""activity time (UTC)"""
	time_end: Optional[datetime] = field( default=None )
	"""activity end time (UTC)"""
	localtime: datetime = field( default=None )
	"""activity time (local)"""
	localtime_end: Optional[datetime] = field( default=None )
	"""activity end time (local)"""
	timezone: str = field( default=get_localzone_name() )
	"""timezone of the activity, local timezone by default"""

	duration: Optional[timedelta] = field( default=None ) #
	duration_moving: Optional[timedelta] = field( default=None ) #

	distance: Optional[float] = field( default=None ) #
	ascent: Optional[float] = field( default=None ) #
	descent: Optional[float] = field( default=None ) #
	elevation_max: Optional[float] = field( default=None ) #
	elevation_min: Optional[float] = field( default=None ) #
	speed: Optional[float] = field( default=None ) #
	speed_max: Optional[float] = field( default=None ) #

	heartrate: Optional[int] = field( default=None ) #
	heartrate_max: Optional[int] = field( default=None ) #
	heartrate_min: Optional[int] = field( default=None ) #
	calories: Optional[int] = field( default=None ) #

	parts: List[ActivityPart] = field( default_factory=list )

	# init variables
	# important: InitVar[str] does not work, dataclass_factory is unable to deserialize, InitVar without types works
	others: InitVar = field( default=None )
	other_parts: InitVar = field( default=None )
	uid: InitVar = field( default=None ) # we keep this as init var

	## internal fields
	__uids__: List[UID] = field( default_factory=list, repr=False, compare=False )
	__dirty__: bool = field( init=False, default=False, repr=False )
	__metadata__: Dict[str, Any] = field( init=False, default_factory=dict )
	__parts__: List[Activity] = field( init=False, default_factory=list, repr=False )
	__resources__: List[Resource] = field( init=False, default_factory=list, repr=False, compare=False )
	__parent__: Activity = field( init=False, default=0 )
	__parent_id__: int = field( init=False, default=0 )

	__vf__: Fields = field( init=False, default=Fields(), hash=False, compare=False )

	# class methods

	@classmethod
	def fields( cls ) -> List[Field]:
		return list( fields( Activity ) )

	@classmethod
	def fieldnames( cls ) -> List[str]:
		return [f.name for f in fields( Activity )]

	@classmethod
	def schema( cls ) -> Schema:
		return Schema(
			omit_default=True,
			skip_internal=True,
			unknown='unknown'
		)

	# additional properties

	@property
	def vf( self ) -> Fields:
		return self.__vf__

	@property
	def classifiers( self ) -> List[str]:
		return unique_sorted( [uid.classifier for uid in self.__uids__] )

	@property
	def local_ids( self ) -> List[int]:
		return sorted( list( set( [int( uid.split( ':', maxsplit=1 )[1] ) for uid in self.uids] ) ) )

	@property
	def as_uids( self ) -> List[UID]:
		return unique_sorted( self.__uids__ )

	@property
	def activity_uids( self ) -> List[str]:
		return unique_sorted( [ f'{uid.classifier}:{uid.local_id}' for uid in self.as_uids ] )

	# dedicated setter for uids to update __uids__ as well
	def set_uids( self, uids: List[str] ) -> None:
		self.uids = unique_sorted( uids )
		self.__uids__ = [UID( uid ) for uid in self.uids]

	@property
	def resources( self ) -> List[Resource]:
		return self.__resources__

	@property
	def parent( self ) -> Optional[Activity]:
		return self.__parent__

	@property
	def parent_id( self ) -> int:
		return self.__parent_id__

	@property
	def group( self ) -> bool:
		return len( self.uids ) > 1

	@property
	def multipart( self ) -> bool:
		return len( self.parts ) > 0

	# post init, this contains mostly convenience things
	def __post_init__( self, others: List[Activity], other_parts: List[Activity], uid: str ):
		# convenience: if called with an uid, store it in uids list + setup __uids__
		if uid:
			self.uids = [uid]

		# uid list handling, depending on parts
		if self.parts:
			self.uids = unique_sorted( uid for p in self.parts for uid in p.activity_uids )

		# sort uids upfront
		if self.uids:
			self.uids = unique_sorted( self.uids )
			self.__uids__ = [UID( uid ) for uid in self.uids]

		# convenience: allow init from other activities
		if others:
			self.union( others )
		elif other_parts:
			self.add( other_parts )

	# additional methods

	# def union( self, others: List[Activity], strategy: Literal['first', 'last'] = 'first' ) -> Activity: # todo: are different strategies useful?
	def union( self, others: List[Activity], ignore: List[str] = None, copy: bool = False, force: bool = False ) -> Activity:
		this = replace( self ) if copy else self
		ignore = ignore if ignore else []

		for f in this.fields():
			if f.name.startswith( '__' ) or f.name in ignore: # never touch internal or ignored fields
				continue

			if not force and f.name in PROTECTED_FIELDS: # only overwrite protected fields when forced
				continue

			value = getattr( this, f.name )

			# case 1: non-factory types
			if f.default != MISSING and f.default_factory == MISSING:
				if not force and value != f.default:  # do not overwrite when a value is already set
					continue

				for other in others:
					# overwrite when other value is different and different from default
					if (other_value := getattr( other, f.name )) != value and other_value != f.default:
						setattr( this, f.name, other_value )
						if not force: # with force the last value wins
							break

			# case 2: factory types
			elif f.default == MISSING and f.default_factory != MISSING:
				for other in others:
					other_value = getattr( other, f.name )
					if f.default_factory is list:
						setattr( this, f.name, sorted( list( set().union( getattr( this, f.name ), other_value ) ) ) )
					elif f.default_factory is dict:
						setattr( this, f.name, { **value, **other_value } )
					else:
						raise RuntimeError( f'unsupported factory datatype: {f.default_factory}' )

		return this

	def add( self, others: List[Activity], copy: bool = False, force: bool = False ) -> Activity:
		"""
		Updates this activity with other activities as parts for this activity.
		Existing values are overwritten, if existing values need to be incorporated, this method
		has to called with add( [ self, other1, other2 ... ] ).

		:return:
		"""

		this = replace( self ) if copy else self
		activities = [this, *others]

		this.type = t if (t := _unique( activities, 'type' ) ) else ActivityTypes.multisport

		this.time = _min( activities, 'time' )
		this.localtime = _min( activities, 'localtime' )
		this.time_end = _max( activities, 'time_end' )
		this.localtime_end = _max( activities, 'localtime_end' )
		this.timezone = t if (t := _unique( activities, 'timezone' ) ) else get_localzone_name()

		this.duration = sum_times( _stream( activities, 'duration' ) )
		this.duration_moving = sum_times( _stream( activities, 'duration_moving' ) )

		this.distance = _sum( activities, 'distance' )
		this.ascent = _sum( activities, 'ascent' )
		this.descent = _sum( activities, 'descent' )
		this.elevation_max = _max( activities, 'elevation_max' )
		this.elevation_min = _min( activities, 'elevation_min' )

		this.speed_max = _max( activities, 'speed_max' )

		this.heartrate_min = _min( activities, 'heartrate_min' )
		this.heartrate_max = _max( activities, 'heartrate_max' )
		this.calories = _sum( activities, 'calories' )

		# todo: fill parts field information already here?

		return this

	def add_resource( self, resource: Resource ) -> None:
		self.__resources__.append( resource )
		resource.__parent_activity__ = self

	def resources_for( self, classifier: str ) -> List[Resource]:
		return [r for r in self.resources if r.uid.startswith( f'{classifier}:' )]

	def tag( self, tag: str ):
		if tag not in self.tags:
			self.tags.append( tag )
			self.tags = sorted( self.tags )

	def untag( self, tag: str ):
		self.tags.remove( tag )

# helper

def _unique( activities: List[Activity], name: str ) -> Any:
	return s.pop() if ( len( s := set( _stream( activities, name ) ) ) == 1 ) else None

def _max( activities: List[Activity], name: str ) -> Any:
	return max( s ) if ( s := _stream( activities, name ) ) else None

def _min( activities: List[Activity], name: str ) -> Any:
	return min( s ) if ( s := _stream( activities, name ) ) else None

def _sum( activities: List[Activity], name: str ) -> Any:
	return sum( s ) if ( s := _stream( activities, name ) ) else None

def _stream( activities: List[Activity], name: str ) -> List:
	return [ v for a in activities if ( v := getattr( a, name, None ) ) ]

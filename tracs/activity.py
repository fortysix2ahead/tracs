
from __future__ import annotations

from dataclasses import dataclass, field, Field, fields, InitVar, MISSING, replace
from datetime import datetime, time
from logging import getLogger
from typing import Any, Callable, ClassVar, Dict, List, Optional

from tzlocal import get_localzone_name

from tracs.activity_types import ActivityTypes
from tracs.resources import Resource, UID
from tracs.utils import sum_times, unique_sorted

log = getLogger( __name__ )

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

	id: int = field( default=0 )
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

	duration: Optional[time] = field( default=None ) #
	duration_moving: Optional[time] = field( default=None ) #

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
	others: InitVar = field( default=None )
	other_parts: InitVar = field( default=None )
	uid: InitVar[str] = field( default=None ) # we keep this as init var

	## internal fields
	__id__: int = field( init=False, default=0, repr=False, compare=False )
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
	def is_group( self ) -> bool:
		return True if len( self.uids ) > 1 else False

	@property
	def multipart( self ) -> bool:
		return len( self.parts ) > 0

	# post init, this contains mostly convenience things
	def __post_init__( self, others: List[Activity], other_parts: List[Activity], uid: str ):
		# id handling needs to be improved later, id field can be an init var
		self.__id__ = self.id

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

	def add( self, others: List[Activity], force: bool = False ) -> Activity:
		"""
		Updates this activity with other activities as parts for this activity.
		Existing values are overwritten, if existing values need to be incorporated, this method
		has to called with add( [ self, other1, other2 ... ] ).

		:return:
		"""

		# field processing is currently a manual process, not sure if this can really be generalized ...
		if others:
			others.sort( key=lambda a: a.time.timestamp() )

			self.time = others[0].time
			self.localtime = others[0].localtime
			self.time_end = others[-1].time_end
			self.localtime_end = others[-1].localtime_end
			self.timezone = others[0].timezone

			self.duration = sum_times( [o.duration for o in others] ) # don't know why pycharm complains about this line
			self.duration_moving = sum_times( [o.duration_moving for o in others] ) # don't know why pycharm complains about this line

			self.distance = s if (s := sum( o.distance for o in others if o.distance )) else None
			self.ascent = s if (s := sum( o.ascent for o in others if o.ascent )) else None
			self.descent = s if (s := sum( o.descent for o in others if o.descent )) else None
			self.elevation_max = max( l ) if ( l := [o.elevation_max for o in others if o.elevation_max is not None] ) else None
			self.elevation_min = min( l ) if ( l := [o.elevation_min for o in others if o.elevation_min is not None] ) else None

			self.speed_max = max( l ) if ( l := [o.speed_max for o in others if o.speed_max is not None] ) else None

			self.heartrate_max = max( l ) if ( l := [o.heartrate_max for o in others if o.heartrate_max is not None] ) else None
			self.heartrate_min = min( l ) if ( l := [o.heartrate_min for o in others if o.heartrate_min is not None] ) else None
			self.calories = s if (s := sum( o.calories for o in others if o.calories )) else None

			# todo: fill parts field information already here?

		return self

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

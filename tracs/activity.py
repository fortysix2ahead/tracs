
from __future__ import annotations

from datetime import datetime, time, timedelta
from logging import getLogger
from typing import Any, Dict, List, Optional, TypeVar, Union

from attrs import define, evolve, Factory, field
from tzlocal import get_localzone_name

from tracs.activity_types import ActivityTypes
from tracs.core import Container, FormattedFieldsBase, VirtualFieldsBase
from tracs.resources import Resource
from tracs.uid import UID
from tracs.utils import sum_timedeltas, unchain, unique_sorted

log = getLogger( __name__ )

T = TypeVar('T')

@define( eq=True )
class ActivityPart:

	gap: time = field( default=None )
	uids: List[str] = field( factory=list )

	__uids__: List[UID] = field( factory=list, alias='__uids__' )

	def __attrs_post_init__(self):
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

@define( eq=True ) # todo: mark fields with proper eq attributes
class Activity( VirtualFieldsBase, FormattedFieldsBase ):

	# fields
	id: int = field( default=None, metadata={ 'protected': True } )
	"""Integer id of this activity, same as key used in dictionary which holds activities, will not be persisted"""
	uid: str = field( default=None, metadata={ 'protected': True } )
	"""UID of this activity"""
	uids: List[str] = field( factory=list, on_setattr=lambda i, a, v: unique_sorted( v ) if v else [], converter=lambda v: unique_sorted( v ), metadata={ 'protected': True } ) # referenced list activities
	"""List of uids of referenced activities"""

	name: Optional[str] = field( default=None )
	"""activity name"""
	type: Optional[ActivityTypes] = field( default=None )
	"""activity type"""
	description: str = field( default=None )
	"""description"""
	tags: List[str] = field( factory=list )
	"""list of tags"""
	equipment: List[str] = field( factory=list )
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

	starttime: datetime = field( default=None )
	"""activity time (UTC)"""
	endtime: Optional[datetime] = field( default=None )
	"""activity end time (UTC)"""
	starttime_local: datetime = field( default=None )
	"""activity time (local)"""
	endtime_local: Optional[datetime] = field( default=None )
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

	parts: List[ActivityPart] = field( factory=list )

	# init variables
	# important: InitVar[str] does not work, dataclass_factory is unable to deserialize, InitVar without types works
	# todo: move this into a factory method?
	others = field( default=None )
	other_parts = field( default=None )

	## internal fields
	__dirty__: bool = field( init=False, default=False, repr=False, alias='__dirty__' )
	__metadata__: Dict[str, Any] = field( init=False, factory=dict, alias='__metadata__' )
	__parts__: List[Activity] = field( init=False, factory=list, repr=False, alias='__parts__' )
	__resources__: List[Resource] = field( init=False, factory=list, repr=False, eq=False, alias='__resources__' )
	__parent__: Optional[Activity] = field( init=False, default=None, alias='__parent__' )
	__parent_id__: int = field( init=False, default=0, alias='__parent_id__' )

	# additional properties

	@property
	def classifiers( self ) -> List[str]:
		return unique_sorted( [uid.classifier for uid in self.refs( as_uid=True )] )

	#@property
	#def local_ids( self ) -> List[int]:
	#	return sorted( list( set( [int( uid.split( ':', maxsplit=1 )[1] ) for uid in self.uids] ) ) )

	def as_uid( self ) -> Optional[UID]:
		return UID( self.uid ) if self.uid else None

	def as_uids( self ) -> List[UID]:
		return [ UID( u ) for u in self.uids ]

	#@property
	#def activity_uids( self ) -> List[str]:
	#	return unique_sorted( [ f'{uid.classifier}:{uid.local_id}' for uid in self.as_uids() ] )

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

	def refs( self, as_uid: bool = False ) -> List[Union[str, UID]]:
		if self.uid and not self.uids:
			return [UID( self.uid )] if as_uid else [self.uid]
		elif self.uids:
			return self.as_uids() if as_uid else self.uids
		else:
			return []

	# post init, this contains mostly convenience things
	def __attrs_post_init__( self ):
		# convenience: allow init from other activities
		if self.others:
			self.union( self.others )
		elif self.other_parts:
			self.add( self.other_parts )

	# additional methods

	def getattr( self, name: str, quiet: bool = False ) -> Any:
		try:
			return getattr( self, name )
		except AttributeError:
			try:
				return self.vf.__fields__.get( name )( self )
			except TypeError:
				if quiet:
					return None
				else:
					raise AttributeError

	# def union( self, others: List[Activity], strategy: Literal['first', 'last'] = 'first' ) -> Activity: # todo: are different strategies useful?
	def union( self, others: List[Activity], ignore: List[str] = None, copy: bool = False, force: bool = False ) -> Activity:
		this = evolve( self ) if copy else self
		ignore = ignore if ignore else []

		for f in this.fields():
			if f.name.startswith( '__' ) or f.name in ignore: # never touch internal or ignored fields
				continue

			if not force and f.metadata.get( 'protected', False ): # only overwrite protected fields when forced
				continue

			value = getattr( this, f.name )

			# case 1: non-factory types
			if not isinstance( f.default, Factory ):
				if not force and value != f.default:  # do not overwrite when a value is already set
					continue

				for other in others:
					# overwrite when other value is different and different from default
					if (other_value := getattr( other, f.name )) != value and other_value != f.default:
						setattr( this, f.name, other_value )
						if not force: # with force the last value wins
							break

			# case 2: factory types
			else:
				for other in others:
					other_value = getattr( other, f.name )
					if f.default.factory is list:
						setattr( this, f.name, sorted( list( set().union( getattr( this, f.name ), other_value ) ) ) )
					elif f.default.factory is dict:
						setattr( this, f.name, { **value, **other_value } )
					else:
						raise RuntimeError( f'unsupported factory datatype: {f.default}' )

		return this

	def add( self, others: List[Activity], copy: bool = False, force: bool = False ) -> Activity:
		"""
		Updates this activity with other activities as parts for this activity.
		Existing values are overwritten, if existing values need to be incorporated, this method
		has to called with add( [ self, other1, other2 ... ] ).

		:return:
		"""

		this = evolve( self ) if copy else self
		activities = [this, *others]

		this.type = t if (t := _unique( activities, 'type' ) ) else ActivityTypes.multisport

		this.starttime = _min( activities, 'starttime' )
		this.starttime_local = _min( activities, 'starttime_local' )
		this.endtime = _max( activities, 'endtime' )
		this.endtime_local = _max( activities, 'endtime_local' )
		this.timezone = t if (t := _unique( activities, 'timezone' ) ) else get_localzone_name()

		this.duration = sum_timedeltas( _stream( activities, 'duration' ) )
		this.duration_moving = sum_timedeltas( _stream( activities, 'duration_moving' ) )

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

@define
class Activities( Container[Activity] ):
	"""
	Dict-like container for activities.
	"""

	# def __attrs_post_init__( self ):
	#	super().__attrs_post_init__()

	def add( self, *activities: Union[Activity, List[Activity]] ) -> List[int]:
		for a in unchain( *activities ):
			# todo: activate insertion checker later
			#if a.uid in self.__uid_map__:
			#	raise KeyError( f'activity with UID {a.uid} already contained in activities' )

			a.id = self.__next_id__()
			self.data.append( a )
			# self.__uid_map__[a.uid] = a
			self.__id_map__[a.id] = a

		return [a.id for a in activities]

	def replace( self, new: Activity, old: Activity = None, id: int = None, uid = None ) -> None:
		if not new:
			return

		old_obj = None
		if old in self.data:
			old_obj = old
		elif id or new.id:
			old_obj = self.idget( id or new.id )
		elif uid or new.uid:
			old_obj = self.get( uid or new.uid )

		if old_obj:
			self.data.remove( old_obj )
			new.id = old_obj.id
			self.data.append( new )

	def remove( self, *ids: Union[int, List[int]] ) -> None:
		for id in unchain( *ids ):
			try:
				self.data.remove( self.idget( id ) )
				del self.__id_map__[id]
			except KeyError:
				pass

# helper

def groups( activities: List[Activity] ) -> List[Activity]:
	return list( filter( lambda a: a.group, activities or [] ) )

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

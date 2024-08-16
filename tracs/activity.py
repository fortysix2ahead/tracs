
from __future__ import annotations

from datetime import datetime, timedelta
from functools import cached_property
from itertools import chain
from logging import getLogger
from typing import Any, ClassVar, Dict, List, Optional, TypeVar, Union

from attrs import define, evolve, Factory, field
from cattrs import Converter, GenConverter
from dateutil.tz import UTC
from more_itertools import first_true
from tzlocal import get_localzone_name

from tracs.activity_types import ActivityTypes
from tracs.core import Container, FormattedFieldsBase, Metadata, VirtualFieldsBase
from tracs.protocols import Importer
from tracs.resources import Resource, Resources
from tracs.uid import UID
from tracs.utils import fromisoformat, str_to_timedelta, sum_timedeltas, timedelta_to_str, toisoformat, unchain, unique_sorted

log = getLogger( __name__ )

T = TypeVar('T')

@define( eq=True )
class ActivityPart:

	converter: ClassVar[Converter] = GenConverter( omit_if_default=True )

	gap: timedelta = field( default=None )
	uid: str = field( factory=list )
	uids: List[str] = field( factory=list )

	@property
	def classifiers( self ) -> List[str]:
		return unique_sorted( [ uid.classifier for uid in self.uid_objs ] )

	@property
	def activity_uids( self ) -> List[str]:
		return [ uid.uid for uid in self.as_activity_uids ]

	@cached_property
	def uid_objs( self ) -> List[UID]:
		return [UID( uid ) for uid in self.uids]

	@property
	def as_uids( self ) -> List[UID]:
		return unique_sorted( self.uid_objs )

	@cached_property
	def as_activity_uids( self ) -> List[UID]:
		return unique_sorted( [ UID( classifier=uid.classifier, local_id=uid.local_id ) for uid in self.uid_objs ] )

	# serialization

	@classmethod
	def from_dict( cls, obj: Dict[str, Any] ) -> ActivityPart:
		return ActivityPart.converter.structure( obj, ActivityPart )

	def to_dict( self ) -> Dict[str, Any]:
		return ActivityPart.converter.unstructure( self )

@define( eq=True ) # todo: mark fields with proper eq attributes
class Activity( VirtualFieldsBase, FormattedFieldsBase ):

	converter: ClassVar[Converter] = GenConverter( omit_if_default=True )

	# fields
	id: int = field( default=None, metadata={ 'protected': True } )
	"""Integer id of this activity, same as key used in dictionary which holds activities, will not be persisted"""
	uid: str = field( default=None, metadata={ 'protected': True } )
	"""UID of this activity"""
	uids: List[str] = field( factory=list, on_setattr=lambda i, a, v: unique_sorted( v ) if v else [], converter=lambda v: unique_sorted( v ), metadata={ 'protected': True } ) # referenced list activities
	"""List of uids of referenced activities"""

	name: str = field( default=None )
	"""activity name"""
	type: ActivityTypes = field( default=None )
	"""activity type"""
	description: str = field( default=None )
	"""description"""
	tags: List[str] = field( factory=list )
	"""list of tags"""
	equipment: List[str] = field( factory=list )
	"""list of equipment tags"""

	location_country: str = field( default=None ) #
	location_state: str = field( default=None ) #
	location_city: str = field( default=None ) #
	location_place: str = field( default=None ) #
	location_latitude_start: float = field( default=None ) #
	location_longitude_start: float = field( default=None ) #
	location_latitude_end: float = field( default=None ) #
	location_longitude_end: float = field( default=None ) #
	route: str = field( default=None ) #

	starttime: datetime = field( default=None, metadata={ 'multipart': 'min' } )
	"""activity time (UTC)"""
	endtime: datetime = field( default=None, metadata={ 'multipart': 'max' } )
	"""activity end time (UTC)"""
	starttime_local: datetime = field( default=None, metadata={ 'multipart': 'min' } )
	"""activity time (local)"""
	endtime_local: datetime = field( default=None, metadata={ 'multipart': 'max' } )
	"""activity end time (local)"""
	timezone: str = field( default=get_localzone_name() )
	"""timezone of the activity, local timezone by default"""

	duration: timedelta = field( default=None ) #
	duration_moving: timedelta = field( default=None ) #

	distance: float = field( default=None, metadata={ 'multipart': 'sum' } ) #
	ascent: float = field( default=None ) #
	descent: float = field( default=None ) #
	elevation_max: float = field( default=None ) #
	elevation_min: float = field( default=None ) #
	speed: float = field( default=None ) #
	speed_max: float = field( default=None ) #

	heartrate: int = field( default=None, metadata={ 'multipart': 'average' } ) #
	heartrate_max: int = field( default=None ) #
	heartrate_min: int = field( default=None ) #
	calories: int = field( default=None ) #

	metadata: Metadata = field( factory=Metadata )
	parts: List[ActivityPart] = field( factory=list )
	resources: Resources = field( factory=Resources ) # todo: merge with Resources later

	# init variables
	# important: InitVar[str] does not work, dataclass_factory is unable to deserialize, InitVar without types works
	# todo: move this into a factory method?
	others = field( default=None )
	other_parts = field( default=None )

	## internal fields
	__dirty__: bool = field( init=False, default=False, repr=False, alias='__dirty__' )
	__parent__: Activity = field( init=False, default=None, alias='__parent__' )
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
	def parent( self ) -> Optional[Activity]:
		return self.__parent__

	@property
	def parent_id( self ) -> int:
		return self.__parent_id__

	@property
	def group( self ) -> bool:
		return len( self.metadata.members ) > 1

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
					elif f.default.factory in [Metadata, Resources]:
						pass # ignore metadata
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

	def resource_of_type( self, resource_type: str ) -> Optional[Resource]:
		return first_true( self.resources.iter(), default=None, pred=lambda r: r.type == resource_type )

	def resources_for( self, classifier: Optional[str], uid: Optional[UID|str] ) -> List[Resource]:
		if classifier:
			return [r for r in self.resources if r.uid.startswith( f'{classifier}:' )]
		elif uid:
			uid = uid if isinstance( uid, str ) else str( uid )
			return [ r for r in self.resources if r.uid == uid ]
		else:
			return self.resources

	def tag( self, tag: str ):
		if tag not in self.tags:
			self.tags.append( tag )
			self.tags = sorted( self.tags )

	def untag( self, tag: str ):
		self.tags.remove( tag )

	@classmethod
	def group_of( cls, *activities: Activity, ignored_fields: List[str] = None, force: bool = False, target: Activity = None ) -> Activity:
		target = target if target else Activity()
		ignored_fields = ignored_fields if ignored_fields else []

		for f in target.fields():
			if f.name.startswith( '__' ) or f.name in ignored_fields: # never touch internal or ignored fields
				continue

			if not force and f.metadata.get( 'protected', False ): # only overwrite protected fields when forced
				continue

			value = getattr( target, f.name )

			# case 1: non-factory types
			if not isinstance( f.default, Factory ):
				if not force and value != f.default:  # do not overwrite when a value is already set
					continue

				for a in activities:
					# overwrite when other value is different and different from default
					if (other_value := getattr( a, f.name )) != value and other_value != f.default:
						setattr( target, f.name, other_value )
						if not force: # with force the last value wins
							break

			# case 2: factory types
			else:
				for a in activities:
					other_value = getattr( a, f.name )
					if f.default.factory is list:
						setattr( target, f.name, sorted( list( set().union( getattr( target, f.name ), other_value ) ) ) )
					elif f.default.factory is dict:
						setattr( target, f.name, { **value, **other_value } )
					elif f.default.factory in [Metadata, Resources]:
						pass
					else:
						raise RuntimeError( f'unsupported factory datatype: {f.default.factory}' )

		# treatment of special fields
		target.uid = f'group:{activities[0].starttime.strftime( "%y%m%d%H%M%S" )}'
		target.metadata.created = datetime.now( UTC )
		target.metadata.members = sorted( [ UID( a.uid ) for a in activities ] )
		target.resources = Resources( lst=sorted( [ r for a in activities for r in a.resources ], key=lambda r: r.path ) )

		return target

	@classmethod
	def multipart_of( cls, *activities: Activity ) -> Activity:
		"""
		Creates a new multipart activity from provided activities.

		:return:
		"""

		mpa = Activity()

		# aggregated fields
		for f in Activity.fields():
			if md := f.metadata.get( 'multipart' ):
				_value = None
				try:
					if md == 'sum':
						_value = sum( values( *activities, name=f.name, filter=True ) )
					elif md == 'max':
						_value = max( values( *activities, name=f.name, filter=True ) )
					elif md == 'min':
						_value = min( values( *activities, name=f.name, filter=True ) )
					elif md == 'average':
						_values = values( *activities, name=f.name, filter=False )
						_durations = values( *activities, name='duration', filter=False )
						_total_duration = sum( [d.seconds for d in _durations] )
						_vd = [ ( v, d.seconds ) for v, d in zip( _values, _durations ) ]
						_value = round( sum( [ v * d / _total_duration  for v, d in _vd ] ) )

				except (AttributeError, TypeError, ValueError):
					log.debug( f'unable to calculate multipart value for field {f.name} from activities { [a.uid for a in activities] }' )

				if _value:
					setattr( mpa, f.name, _value )

		# create part objects
		activities = sorted( [*activities], key=lambda a: a.starttime )
		mpa.parts = [ ActivityPart( uids=[a.uid] ) for a in activities ]
		mpa.parts[0].gap = timedelta( seconds=0 )
		for i in range( 1, len( activities ) ):
			mpa.parts[i].gap = activities[i].starttime - activities[i-1].endtime

		# type + uid
		mpa.type = t if (t := _unique( activities, 'type' ) ) else ActivityTypes.multisport
		mpa.uids = list( set( a.uid for a in activities ) )

		return mpa

	# serialization

	@classmethod
	def from_dict( cls, obj: Dict[str, Any] ) -> Activity:
		return Activity.converter.structure( obj, Activity )

	def to_dict( self ) -> Dict[str, Any]:
		return Activity.converter.unstructure( self )

@define
class Activities( Container[Activity] ):

	converter: ClassVar[Converter] = GenConverter( omit_if_default=True )

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

	def iter( self ):
		return iter( self.data )

	def iter_resources( self ):
		return chain( *[ a.resources for a in self.data ] )

	# serialization

	@classmethod
	def from_dict( cls, obj: List[Dict] ) -> Activities:
		return Activities( data=[Activity.from_dict( o ) for o in obj] )

	def to_dict( self ) -> List[Dict]:
		return [ Activity.to_dict( a ) for a in self.all( sort=True ) ]

# helper

def values( *activities: Activity, name: str, filter: bool = False ) -> List:
	_values = [ getattr( a, name, None ) for a in activities ]
	return [ v for v in _values if v is not None ] if filter else _values

def groups( activities: List[Activity] ) -> List[Activity]:
	return [a for a in activities if a.group]

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

# configure converters

ActivityPart.converter.register_unstructure_hook( timedelta, timedelta_to_str )
ActivityPart.converter.register_structure_hook( timedelta, lambda obj, cls: str_to_timedelta( obj ) )

Activity.converter.register_unstructure_hook( datetime, toisoformat )
Activity.converter.register_unstructure_hook( timedelta, timedelta_to_str )
Activity.converter.register_unstructure_hook( ActivityTypes, ActivityTypes.to_str )
Activity.converter.register_unstructure_hook( Metadata, lambda md: md.to_dict() )
Activity.converter.register_unstructure_hook( Resources, lambda rl: rl.to_dict() )

Activity.converter.register_structure_hook( int, lambda obj, cls: int( obj ) if obj is not None else None )
Activity.converter.register_structure_hook( datetime, lambda obj, cls: fromisoformat( obj ) )
Activity.converter.register_structure_hook( timedelta, lambda obj, cls: str_to_timedelta( obj ) )
Activity.converter.register_structure_hook( ActivityTypes, lambda obj, cls: ActivityTypes.from_str( obj ) )
Activity.converter.register_structure_hook( Metadata, lambda obj, cls: Metadata.from_dict( obj ) )
Activity.converter.register_structure_hook( Resources, lambda obj, cls: Resources.from_dict( obj ) )

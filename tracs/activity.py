
from __future__ import annotations

from collections import UserList
from datetime import datetime, timedelta
from inspect import isfunction
from itertools import chain, pairwise
from logging import getLogger
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, List, Literal, Mapping, Optional, TypeVar, Union

from attrs import fields
from attrs import define, evolve, Factory, field
from dateutil.tz import UTC
from more_itertools import first, first_true, last, unique
from tzlocal import get_localzone_name

from tracs.activity_types import ActivityTypes
from tracs.core import FieldFormatters, Metadata, VirtualFields
from tracs.resources import Resource, Resources
from tracs.ui.utils import fmt_datetime, fmt_decimal, fmt_default, fmt_timedelta
from tracs.uid import UID, uid
from tracs.utils import sum_timedeltas, unique_sorted

log = getLogger( __name__ )

T = TypeVar('T')
MULTIPART_TYPE: type[str] = Literal[ 'average', 'max', 'min', 'sum' ]

@define( eq=True, repr=False ) # todo: mark fields with proper eq attributes
class Activity:

	# class fields to add support for virtual fields + formatters
	__vf__: ClassVar[VirtualFields] = VirtualFields()
	__fmf__: ClassVar[FieldFormatters] = FieldFormatters()

	# fields
	id: int = field( default=None, metadata={ 'protected': True } )
	"""Integer id of this activity, same as key used in dictionary which holds activities.
	May be changed to str in the future."""

	uid: UID|str = field(
		default=None,
		converter=lambda u: UID.from_str( u ) if isinstance( u, str ) else u,
		metadata={ 'protected': True }
	)

	# actual activitiy fields
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
	elevation: float = field( default=None ) #
	elevation_max: float = field( default=None ) #
	elevation_min: float = field( default=None ) #
	speed: float = field( default=None ) #
	speed_max: float = field( default=None ) #

	cadence: float = field( default=None ) #
	cadence_max: float = field( default=None ) #
	power: float = field( default=None ) #
	power_max: float = field( default=None ) #

	heartrate: int = field( default=None, metadata={ 'multipart': 'average' } ) #
	heartrate_max: int = field( default=None ) #
	heartrate_min: int = field( default=None ) #
	calories: int = field( default=None ) #

	metadata: Metadata = field( factory=Metadata )
	resources: Resources = field( factory=Resources ) # todo: merge with Resources later

	# todo: this needs to be moved into MultipartActivity/ActivityGroup
	other_parts = field( default=None )

	## internal fields
	__member_of__: ActivityGroup = field( init=False, default=None, alias='__member_of__' )
	__part_of__: List[MultipartActivity] = field( init=False, default=None, alias='__part_of__' )

	__dirty__: bool = field( init=False, default=False, repr=False, alias='__dirty__' )
	__fields_proxy__: VirtualFields = field( default=None, alias='__fields_proxy__' )

	@classmethod
	def virtual_fields( cls ) -> VirtualFields:
		return cls.__vf__

	def vf( self ) -> VirtualFields:
		if self.__fields_proxy__ is None:
			self.__fields_proxy__ = VirtualFields( self.__class__.__vf__.data, self )
		return self.__fields_proxy__

	def of( self, id: int = 0, uid: str = 'activity:0', name: str = 'Activity 0' ):
		pass

	@property
	def classifier( self ) -> str:
		return self.uid.classifier

	@property
	def classifiers( self ) -> List[str]:
		if self.group:
			return list( unique( [ m.classifier for m in self.metadata.members ] ) )
		elif self.multipart:
			pass # todo: add multipart support
		else:
			return [ self.uid.classifier ]

	@property
	def uids( self ) -> List[str]:
		if self.group:
			return list( unique( [ m.as_tuple_str for m in self.metadata.members ] ) )
		elif self.multipart:
			pass # todo: add multipart support
		else:
			return [ self.uid.as_tuple_str ]

	#@property
	#def local_ids( self ) -> List[int]:
	#	return sorted( list( set( [int( uid.split( ':', maxsplit=1 )[1] ) for uid in self.uids] ) ) )

	#@property
	#def activity_uids( self ) -> List[str]:
	#	return unique_sorted( [ f'{uid.classifier}:{uid.local_id}' for uid in self.as_uids() ] )

	@property
	def group( self ) -> bool:
		return len( self.metadata.members ) > 1

	@property
	def multipart( self ) -> bool:
		return False

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
		if self.other_parts:
			self.add( self.other_parts )

	def __repr__( self ) -> str:
		return f'{self.name} [{self.uid}] [{self.starttime}]'

	# additional methods

	def add_resource( self, resource: Resource ) -> None:
		self.__resources__.append( resource )
		resource.__parent_activity__ = self

	def resource_of_type( self, resource_type: str ) -> Optional[Resource]:
		return first_true( self.resources.iter(), default=None, pred=lambda r: r.name == resource_type )

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
	def union( cls, *activities: Activity, ignored_fields: List[str] = None, force: bool = False, target: Activity = None ) -> Activity:
		target = target or Activity()
		ignored_fields = ignored_fields or []

		for f in fields( Activity ):
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
		# todo: really set target uid or leave it untouched?
		target.uid = last( activities ).uid if force else first( activities ).uid

		# update times
		target.metadata.modified = datetime.now( UTC )
		if not target.metadata.created:
			target.metadata.created = target.metadata.modified

		return target

@define
class ActivityGroup( Activity ):

	__members__: List[Activity] = field( factory=list, alias='__members__' )

	@property
	def group( self ) -> bool:
		return True

	@classmethod
	def of( cls, *activities: Activity, ignored_fields: List[str] = None, force: bool = False, target: Activity = None ) -> ActivityGroup:
		if target is not None and not isinstance( target, ActivityGroup ):
			raise ValueError( 'target must be an instance of ActivityGroup' )

		if target is None:
			target = ActivityGroup()

		target = cls.union( *activities, ignored_fields=ignored_fields, force=force, target=target )

		# treatment of special fields
		if target.uid.classifier != 'group':
			target.uid = uid( f'group:{activities[0].starttime.strftime( "%y%m%d%H%M%S" )}' )

		# update members
		target.metadata.members = sorted( [a.uid for a in activities] )
		for a in activities:
			a.metadata.member_of = target.uid

		return target

@define( repr=False )
class MultipartActivity( Activity ):

	gaps: List[timedelta] = field( factory=list ) # this is always len( parts ) - 1

	# internal fields
	__parts__: List[Activity] = field( factory=list, alias='__parts__' )

	@property
	def gaps_before( self ) -> List[timedelta]:
		return [ timedelta(), *self.gaps ]

	@property
	def gaps_after( self ) -> List[timedelta]:
		return [ *self.gaps, timedelta() ]

	@property
	def multipart( self ) -> bool:
		return True

	def __repr__( self ) -> str:
		return super().__repr__()

	@classmethod
	def of( cls, *activities: Activity, target: MultipartActivity = None ) -> MultipartActivity:
		"""Creates a new multipart activity from provided activities.

		:return: new multipart activity
		"""
		if len( activities ) < 2:
			raise ValueError( 'unable to create a multipart activity with less than 2 parts' )

		if target is not None and not isinstance( target, MultipartActivity ):
			raise ValueError( 'target must be an instance of MultipartActivity' )

		if target is None:
			target = MultipartActivity()

		# aggregated fields
		for f in fields( Activity ):
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
					setattr( target, f.name, _value )

		# create parts
		activities = sorted( [*activities], key=lambda a: a.starttime )
		target.gaps = [succ.starttime - pred.endtime for pred, succ in pairwise( activities )]

		# update metadata
		target.uid = uid( f'multipart:{activities[0].starttime.strftime( "%y%m%d%H%M%S" )}' )
		target.metadata.parts = [ a.uid for a in activities ]
		for a in activities:
			a.metadata.part_of.append( target.uid )

		# update type
		target.type = t if (t := _unique( activities, 'type' ) ) else ActivityTypes.multisport

		return target


class Activities( UserList[Activity] ):
	"""
	Extended list of activities.
	"""

	def __init__( self, *activities: Activity, lst: Optional[List[Activity]] = None, skip_checks: bool = False ):
		super().__init__()

		self._id_idx: Dict[int, Activity] = dict()
		self._uid_idx: Dict[UID, Activity] = dict()
		self.add( *activities, lst=lst, skip_checks=skip_checks )

	# calculation of next id
	def __next_id__( self ) -> int:
		existing_ids = [a.id for a in self]
		id_range = range( 1, max( existing_ids ) + 2 ) if len( existing_ids ) > 0 else [1]
		return set( id_range ).difference( set( existing_ids ) ).pop()

	def __next_id_2__( self ) -> int:
		return max( self._id_idx.keys() ) + 1 if self._id_idx else 1

	def __contains__( self, item: Activity|UID ) -> bool:
		if isinstance( item, Activity ):
			return super().__contains__( item )
		elif isinstance( item, UID ):
			return self.__contains_uid__( item )
		else:
			return False

	def __delitem__( self, i: int ):
		self.remove( self.data[i] )

	def __remove__( self, a: Activity ):
		del self._id_idx[a.id]
		del self._uid_idx[a.uid]
		self.data.remove( a )

	def __contains_uid__( self, uid: UID ):
		# old version without index
		# return any( [a.uid == uid for a in self] )
		return uid in self._uid_idx

	# def replace( self, new: Activity, old: Activity = None, id: int = None, uid = None ) -> None:
	# 	if not new:
	# 		return
	#
	# 	old_obj = None
	# 	if old in self.data:
	# 		old_obj = old
	# 	elif id or new.id:
	# 		old_obj = self.idget( id or new.id )
	# 	elif uid or new.uid:
	# 		old_obj = self.get( uid or new.uid )
	#
	# 	if old_obj:
	# 		self.data.remove( old_obj )
	# 		new.id = old_obj.id
	# 		self.data.append( new )

	def add( self, *activities: Activity, lst: Optional[List[Activity]] = None, skip_checks: bool = False ) -> List[int]:
		activities = [ *activities, *(lst if lst else []) ]

		for a in activities:
			if not skip_checks:
				if a.uid is None:
					raise KeyError( f'activity must have a valid UID to be added (UID = {a.uid})' )
				if self.__contains_uid__( a.uid ):
					raise KeyError( f'activity with UID {a.uid} already contained in activities' )

				a.id = self.__next_id_2__()

			self._id_idx[a.id] = a
			self._uid_idx[a.uid] = a

		self.data.extend( activities )

		return [a.id for a in activities]

	def remove( self, item: UID|str|Activity ):
		if isinstance( item, Activity ) and item in self.data:
			self.__remove__( item )
		elif item in self._id_idx or item in self._uid_idx:
			self.__remove__( self._id_idx.get( item ) or self._uid_idx.get( item ) )

	def all( self, sort: bool|Callable = False, reverse: bool = False ) -> List[Activity]:
		if sort is True:
			return sorted( self.data, key=lambda a: a.id, reverse=reverse )
		elif isfunction( sort ):
			return sorted( self.data, key=sort, reverse=reverse )
		else:
			return list( self.data )

	def ids( self ) -> List[int]:
		return list( self._id_idx.keys() )

	def uids( self ) -> List[UID]:
		return list( self._uid_idx.keys() )

	@property
	def id_map( self ) -> Mapping[int, Activity]:
		return MappingProxyType( self._id_idx )

	@property
	def uid_map( self ) -> Mapping[UID, Activity]:
		return MappingProxyType( self._uid_idx )

	def get( self, uid: UID|str ) -> Optional[Activity]:
		return self._uid_idx.get( uid )

	def get_by_id( self, id: int ) -> Optional[Activity]:
		return self._id_idx.get( id )

	def get_by_uid( self, uid: UID|str ) -> Optional[Activity]:
		return self._uid_idx.get( uid )

	def idget( self, id: int ) -> Optional[Activity]:
		return self._id_idx.get( id )

	def iter( self ):
		return self.data.__iter__()

	def iter_regular( self ):
		return filter( lambda a: not a.group and not a.multipart, self.data.__iter__() )

	def iter_groups( self ):
		return filter( lambda a: a.group, self.data.__iter__() )

	def iter_non_groups( self ):
		return filter( lambda a: not a.group, self.data.__iter__() )

	def iter_multiparts( self ):
		return filter( lambda a: a.multipart, self.data.__iter__() )

	def iter_resources( self ) -> Resources:
		return Resources( *chain( *[ a.resources for a in self ] ) )

	def iter_uids( self ):
		return chain( *[ [ a.uid, *a.metadata.members ] for a in self ] )

	def iter_resource_uids( self ):
		return chain( *[ [ r.as_uid if r.uid else UID( *a.uid.as_tuple, r.path ) for r in a.resources ] for a in self ] )

# helper

def values( *activities: Activity, name: str, filter: bool = False ) -> List:
	_values = [ getattr( a, name, None ) for a in activities ]
	return [ v for v in _values if v is not None ] if filter else _values

def groups( activities: List[Activity] ) -> List[Activity]:
	return [a for a in activities if a.group] if activities else []

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

# configure formatting
# todo: don't like that as field names are already pinned down here

# Activity.__fmf__['__default__'] = fmt_default
# for f in [ 'starttime', 'starttime_local', 'endtime', 'endtime_local' ]:
# 	Activity.__fmf__[f] = fmt_datetime
# for f in [ 'duration', 'duration_moving' ]:
# 	Activity.__fmf__[f] = fmt_timedelta
# for f in [ 'distance', 'ascent', 'descent', 'elevation', 'elevation_max', 'elevation_min', 'speed', 'speed_max' ]:
# 	Activity.__fmf__[f] = fmt_decimal
#
# # noinspection PyShadowingNames
def configure_formatters( cfg: Dict ):
	pass
	# for f in ['starttime', 'starttime_local', 'endtime', 'endtime_local']:
	# 	if formatter := Activity.field_formatters().get( f ):
	# 		formatter.format, formatter.locale = cfg.get( 'datetime' ), cfg.get( 'locale' )
	# for f in [ 'duration', 'duration_moving' ]:
	# 	if formatter := Activity.field_formatters().get( f ):
	# 		formatter.format, formatter.locale = cfg.get( 'timedelta' ), cfg.get( 'locale' )
	# for f in [ 'distance', 'ascent', 'descent', 'elevation', 'elevation_max', 'elevation_min', 'speed', 'speed_max' ]:
	# 	if formatter := Activity.field_formatters().get( f ):
	# 		formatter.locale = cfg.get( 'locale' )

from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, List, Optional, Union

from attrs import define, field
from dateutil.parser import parse as parse_dt
from dateutil.tz import tzlocal
from lxml.objectify import Element, fromstring, ObjectifiedElement, ObjectPath, SubElement

from tracs.activity import Activity as TracsActivity
from tracs.pluginmgr import importer, resourcetype
from tracs.plugins.xml import XMLHandler
from tracs.resources import Resource, ResourceType
from tracs.utils import fromisoformat

log = getLogger( __name__ )

TCX_TYPE = 'application/tcx+xml'

@define
class Extensions:
	other_elements: List = field( factory=list )

@define
class Trackpoint:

	__xml_name__ = 'Trackpoint'

	time: Union[datetime, str] = field( default=None )
	latitude_degrees: float = field( default=None )
	longitude_degrees: float = field( default=None )
	altitude_meters: float = field( default=None )
	distance_meters: float = field( default=None )
	heart_rate_bpm: float = field( default=None )
	sensor_state: str = field( default=None )
	cadence: int = field( default=None )
	extensions: Optional[Extensions] = field( default=None )

	def __post_init__( self ):
		self.time = parse_dt( self.time ) if type( self.time ) is str else self.time
		self.sensor_state = 'Present' # use this as pseudo-default

	def as_xml( self, parent: Element ) -> Element:
		trackpoint = SubElement( parent, Trackpoint.__xml_name__ )
		sub( trackpoint, 'Time', ztime( self.time ) )
		if self.latitude_degrees is not None and self.longitude_degrees is not None:
			position = SubElement( trackpoint, 'Position' )
			sub( position, 'LatitudeDegrees', self.latitude_degrees )
			sub( position, 'LongitudeDegrees', self.longitude_degrees )
		sub( trackpoint, 'AltitudeMeters', self.altitude_meters )
		sub( trackpoint, 'DistanceMeters', self.distance_meters )
		sub2( trackpoint, 'HeartRateBpm', 'Value', self.heart_rate_bpm )
		sub( trackpoint, 'Cadence', self.cadence )
		sub( trackpoint, 'SensorState', self.sensor_state )
		return trackpoint

	@classmethod
	def from_xml( cls, parent: Element ) -> List[Trackpoint]:
		return [
			Trackpoint(
				time=find( tp, 'Time' ),
				latitude_degrees=find( tp, 'Position.LatitudeDegrees' ),
				longitude_degrees=find( tp, 'Position.LongitudeDegrees' ),
				altitude_meters=find( tp, 'AltitudeMeters' ),
				distance_meters=find( tp, 'DistanceMeters' ),
				heart_rate_bpm=find( tp, 'HeartRateBpm.Value' ),
				cadence=find( tp, 'Cadence' ),
				sensor_state=find( tp, 'SensorState' ),
			) for tp in parent.Track.Trackpoint
		]

@define
class Lap:

	__xml_name__ = 'Lap'

	start_date: datetime = field( default=None )
	total_time_seconds: float = field( default=None )
	distance_meters: float = field( default=None )
	maximum_speed: float = field( default=None )
	calories: int = field( default=None )
	average_heart_rate_bpm: int = field( default=None )
	maximum_heart_rate_bpm: int = field( default=None )
	cadence: int = field( default=None )
	intensity: str = field( default=None )
	trigger_method: str = field( default=None )
	trackpoints: List[Trackpoint] = field( factory=list )
	notes: Optional[str] = field( default=None )
	extensions: Optional[Extensions] = field( default=None )

	def __post_init__( self ):
		pass

	@property
	def time( self ) -> Optional[datetime]:
		return self.trackpoints[0].time if len( self.trackpoints ) else None

	@property
	def time_end( self ) -> Optional[datetime]:
		return self.trackpoints[-1].time if len( self.trackpoints ) else None

	def as_xml( self, parent: Element ) -> Element:
		lap = SubElement( parent, Lap.__xml_name__, attrib={'StartTime': ztime( self.start_date )} )
		sub( lap, 'TotalTimeSeconds', self.total_time_seconds )
		sub( lap, 'DistanceMeters', self.distance_meters )
		sub( lap, 'MaximumSpeed', self.maximum_speed )
		sub( lap, 'Calories', self.calories )
		sub2( lap, 'AverageHeartRateBpm', 'Value', self.average_heart_rate_bpm )
		sub2( lap, 'MaximumHeartRateBpm', 'Value', self.maximum_heart_rate_bpm )
		sub( lap, 'Intensity', self.intensity )
		sub( lap, 'Cadence', self.cadence )
		sub( lap, 'TriggerMethod', self.trigger_method )
		track = SubElement( lap, 'Track' )
		trackpoints = [ tp.as_xml( track ) for tp in self.trackpoints ]
		return lap

	@classmethod
	def from_xml( cls, parent: Element ) -> List[Lap]:
		return [
			Lap(
				start_date=l.get( 'StartTime' ),
				total_time_seconds=find( l, 'TotalTimeSeconds' ),
				distance_meters=find( l, 'DistanceMeters' ),
				maximum_speed=find( l, 'MaximumSpeed' ),
				calories=find( l, 'Calories' ),
				average_heart_rate_bpm=find( l, 'AverageHeartRateBpm.Value' ),
				maximum_heart_rate_bpm=find( l, 'MaximumHeartRateBpm.Value' ),
				intensity=find( l, 'Intensity' ),
				cadence=find( l, 'Cadence' ),
				trigger_method=find( l, 'TriggerMethod' ),
				trackpoints=Trackpoint.from_xml( l ),
			) for l in parent.Lap
		]

@define
class Plan:

	__xml_name__ = 'Plan'

	name: Optional[str] = field( default=None )
	extensions: Optional[Extensions] = field( default=None )
	type: Optional[str] = field( default=None )
	interval_workout: Optional[bool] = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		return SubElement( parent, self.__class__.__xml_name__, attrib={ 'Type': self.type, 'IntervalWorkout': str( self.interval_workout ).lower() } )

@define
class Training:

	__xml_name__ = 'Training'

	virtual_partner: str = field( default=None )
	plan: Plan = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		training = SubElement( parent, self.__class__.__xml_name__, attrib={ 'VirtualPartner': self.virtual_partner } )
		plan = self.plan.as_xml( training )
		return training

@define
class Creator:

	__xml_name__ = 'Creator'

	name: str = field( default=None )
	unit_id: int = field( default=None )
	product_id: int = field( default=None )
	version_major: int = field( default=None )
	version_minor: int = field( default=None )
	version_build_major: int = field( default=None )
	version_build_minor: int = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		creator = SubElement( parent, self.__class__.__xml_name__ )
		sub( creator, 'Name', self.name )
		sub( creator, 'UnitId', self.unit_id )
		sub( creator, 'ProductID', self.product_id )
		version = SubElement( creator, 'Version' )
		sub( version, 'VersionMajor', self.version_major )
		sub( version, 'VersionMinor', self.version_minor )
		sub( version, 'BuildMajor', self.version_build_major )
		sub( version, 'BuildMinor', self.version_build_minor )
		return creator

	@classmethod
	def from_xml( cls, parent: Element ) -> Optional[Creator]:
		if e := elem( parent, cls.__xml_name__ ):
			return Creator(
				name=find( e, 'Name' ),
				unit_id=find( e, 'UnitId' ),
				product_id=find( e, 'ProductID' ),
				version_major=find( e, 'Version.VersionMajor' ),
				version_minor=find( e, 'Version.VersionMajor' ),
				version_build_major=find( e, 'Version.BuildMajor' ),
				version_build_minor=find( e, 'Version.BuildMinor' ),
			)
		else:
			return None


@define
class Activity:

	__xml_name__ = 'Activity'

	id: str = field( default=None )
	laps: List[Lap] = field( factory=list )
	notes: Optional[str] = field( default=None )
	training: Optional[Training] = field( default=None )
	creator: Optional[Creator] = field( default=None )
	# extensions: Optional[Extensions] = field( default=None )
	# sport: Optional[Sport] = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		activity = SubElement( parent, self.__class__.__xml_name__ )
		id = sub( activity, 'Id', self.id )
		laps = [ l.as_xml( activity ) for l in self.laps ]
		training = self.training.as_xml( activity ) if self.training else None # todo: may this be None?
		creator = self.creator.as_xml( activity ) if self.creator else None
		return activity

	@classmethod
	def from_xml( cls, parent: Element ) -> List[Activity]:
		return [
			Activity(
				id = a.Id, # or find( c, 'Id' )
				laps = Lap.from_xml( a ),
				creator = Creator.from_xml( a ),
			) for a in parent.Activities.Activity
		]

@define
class Author:

	__xml_name__ = 'Author'

	name: str = field( default=None )
	build_version_major: int = field( default=None )
	build_version_minor: int = field( default=None )
	lang_id: str = field( default=None )
	part_number: str = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		author = SubElement( parent, Author.__xml_name__ )
		sub( author, 'Name', self.name )
		build = SubElement( author, 'Build' )
		version = SubElement( build, 'Version' )
		sub( version, 'VersionMajor', self.build_version_major )
		sub( version, 'VersionMinor', self.build_version_minor )
		sub( author, 'LangID', self.lang_id )
		sub( author, 'PartNumber', self.part_number )
		return author

	@classmethod
	def from_xml( cls, parent: Element ) -> Optional[Author]:
		if e := elem( parent, cls.__xml_name__ ):
			return Author(
				name=find( e, 'Name' ) # todo: complete author
			)
		else:
			return None

@define
class TrainingCenterDatabase:

	__xml_name__ = 'TrainingCenterDatabase'

	# folders: Optional[Folders] = field( default=None )
	activities: List[Activity] = field( factory=list )
	# workouts: Optional[WorkoutList] = field( default=None )
	# courses: Optional[CourseList] = field( default=None )
	author: Optional[Author] = field( default=None )
	# extensions: Optional[Extensions] = field( default=None )

	@property
	def distance( self ) -> float:
		return sum( l.distance_meters for a in self.activities for l in a.laps )

	@property
	def duration( self ) -> timedelta:
		return timedelta( seconds = (self.time_end - self.time).total_seconds() )

	@property
	def time( self ) -> Optional[datetime]:
		if len( self.activities ) and len( self.activities[0].laps ):
			return fromisoformat( self.activities[0].laps[0].time )
		else:
			return None

	@property
	def time_end( self ) -> Optional[datetime]:
		if len( self.activities ) and len( self.activities[0].laps ):
			return fromisoformat( self.activities[-1].laps[-1].time_end )
		else:
			return None

	def as_xml( self ) -> Element:
		root = Element( self.__class__.__xml_name__ )
		activities_element = SubElement( root, 'Activities' )
		activities = [ a.as_xml( activities_element ) for a in self.activities ]
		author = self.author.as_xml( root ) if self.author else None
		return root

	@classmethod
	def from_xml( cls, root ) -> Any:
		return TrainingCenterDatabase(
			activities=Activity.from_xml( root ),
			author=Author.from_xml( root ),
		)

@resourcetype
def tcx_resource_type() -> ResourceType:
	return ResourceType( type=TCX_TYPE, recording=True )

@importer
class TCXImporter( XMLHandler ):

	TYPE: str = TCX_TYPE
	ACTIVITY_CLS = Activity

	def load_raw( self, content: Union[bytes, str], **kwargs ) -> Any:
		return fromstring( content )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		return TrainingCenterDatabase.from_xml( raw )

	def save_data( self, data: Any, **kwargs ) -> Any:
		return data

	def as_activity( self, resource: Resource ) -> Optional[TracsActivity]:
		tcx: TrainingCenterDatabase = resource.data
		return TracsActivity(
			distance=tcx.distance,
			duration=tcx.duration,
			starttime=tcx.time,
			endtime=tcx.time_end,
			starttime_local=tcx.time.astimezone( tzlocal() ),
			endtime_local=tcx.time_end.astimezone( tzlocal() ),
			uid=f'tcx:{tcx.time.strftime( "%y%m%d%H%M%S" )}',
		)

# helper

def ztime( dt: datetime ) -> str:
	return dt.strftime( '%Y-%m-%dT%H:%M:%SZ' ) if dt else None

def find( element: ObjectifiedElement, sub_element: str ) -> Any:
	try:
		return ObjectPath( f'.{sub_element}' ).find( element ).pyval
	except AttributeError:
		return None

def elem( element: ObjectifiedElement, sub_element: str ) -> Optional[Element]:
	try:
		return ObjectPath( f'.{sub_element}' ).find( element )
	except AttributeError:
		return None

# noinspection PyProtectedMember
def sub( parent: Element, name: str, value: Any ) -> Optional[SubElement]:
	if value is not None and value != 0 and value != 0.0:
		sub_element = SubElement( parent, name )
		sub_element._setText( str( value ) ) # todo: that is the way it is supposed to work??? WTF?
		return sub_element
	else:
		return None

def sub2( parent: Element, name_1: str, name_2: str, value: Any ) -> Optional[SubElement]:
	sub_element = SubElement( parent, name_1 )
	sub( sub_element, name_2, value )
	return sub_element

def sub3( parent: Element, name_1: str, name_2: str, name_3: str, value: Any ) -> Optional[SubElement]:
	sub_element = SubElement( parent, name_1 )
	sub2( sub_element, name_2, name_3, value )
	return sub_element


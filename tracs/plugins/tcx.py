from dataclasses import dataclass, field
from datetime import datetime, time
from logging import getLogger
from typing import Any, List, Optional, Union

from dateutil.parser import parse as parse_dt
from dateutil.tz import tzlocal
from lxml.objectify import Element, fromstring, ObjectifiedElement, ObjectPath, SubElement

from tracs.plugins.xml import XMLHandler
from tracs.activity import Activity as TracsActivity
from ..registry import importer
from ..resources import Resource
from ..utils import seconds_to_time

log = getLogger( __name__ )

TCX_TYPE = 'application/tcx+xml'

@dataclass
class Extensions:
	other_elements: List = field( default_factory=list )

@dataclass
class Trackpoint:

	__xml_name__ = 'Trackpoint'

	time: Union[datetime, str] = field( default=None )
	latitude_degrees: float = field( default=None )
	longitude_degrees: float = field( default=None )
	altitude_meters: float = field( default=None )
	distance_meters: float = field( default=None )
	dist: float = field( default=None )
	heart_rate_bpm: float = field( default=None )
	sensor_state: str = field( default=None )
	cadence: int = field( default=None )
	extensions: Optional[Extensions] = field( default=None )

	def __post_init__( self ):
		self.time = parse_dt( self.time ) if type( self.time ) is str else self.time

	def as_xml( self, parent: Element ) -> Element:
		trackpoint = SubElement( parent, Trackpoint.__xml_name__ )
		sub( trackpoint, 'Time', self.time )
		position = SubElement( trackpoint, 'Position' )
		sub( position, 'LatitudeDegrees', self.latitude_degrees )
		sub( position, 'LongitudeDegrees', self.longitude_degrees )
		sub( trackpoint, 'AltitudeMeters', self.altitude_meters )
		sub( trackpoint, 'DistanceMeters', self.distance_meters )
		sub2( trackpoint, 'HeartRateBpm', 'Value', self.heart_rate_bpm )
		sub( trackpoint, 'Cadence', self.cadence )
		sub( trackpoint, 'SensorState', self.sensor_state )
		return trackpoint

@dataclass
class Lap:

	__xml_name__ = 'Lap'

	start_time: datetime = field( default=None )
	total_time_seconds: float = field( default=None )
	distance_meters: float = field( default=None )
	maximum_speed: float = field( default=None )
	calories: int = field( default=None )
	average_heart_rate_bpm: int = field( default=None )
	maximum_heart_rate_bpm: int = field( default=None )
	cadence: int = field( default=None )
	intensity: str = field( default=None )
	trigger_method: str = field( default=None )
	trackpoints: List[Trackpoint] = field( default_factory=list )
	notes: Optional[str] = field( default=None )
	extensions: Optional[Extensions] = field( default=None )

	def __post_init__( self ):
		pass

	def time( self ) -> Optional[datetime]:
		return self.points[0].time if len( self.points ) > 0 else None

	def time_end( self ) -> Optional[datetime]:
		return self.points[-1].time if len( self.points ) > 0 else None

	def as_xml( self, parent: Element ) -> Element:
		lap = SubElement( parent, Lap.__xml_name__, attrib={'StartTime': str( self.start_time )} )
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

@dataclass
class Plan:

	__xml_name__ = 'Plan'

	name: Optional[str] = field( default=None )
	extensions: Optional[Extensions] = field( default=None )
	type: Optional[str] = field( default=None )
	interval_workout: Optional[bool] = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		return SubElement( parent, self.__class__.__xml_name__, attrib={ 'Type': self.type, 'IntervalWorkout': str( self.interval_workout ).lower() } )

@dataclass
class Training:

	__xml_name__ = 'Training'

	virtual_partner: str = field( default=None )
	plan: Plan = field( default=None )

	def as_xml( self, parent: Element ) -> Element:
		training = SubElement( parent, self.__class__.__xml_name__, attrib={ 'VirtualPartner': self.virtual_partner } )
		plan = self.plan.as_xml( training )
		return training

@dataclass
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

@dataclass
class Activity:

	__xml_name__ = 'Activity'

	id: str = field( default=None )
	laps: List[Lap] = field( default_factory=list )
	notes: Optional[str] = field( default=None )
	training: Optional[Training] = field( default=None )
	creator: Optional[Creator] = field( default=None )
	# extensions: Optional[Extensions] = field( default=None )
	# sport: Optional[Sport] = field( default=None )

	def distance( self ) -> float:
		return sum( l.distance for l in self.laps )

	def duration( self ) -> time:
		return seconds_to_time( (self.time_end() - self.time()).total_seconds() )

	def time( self ) -> Optional[datetime]:
		return self.laps[0].time() if len( self.laps ) > 0 else None

	def time_end( self ) -> Optional[datetime]:
		return self.laps[-1].time_end() if len( self.laps ) > 0 else None

	def as_xml( self, parent: Element ) -> Element:
		activity = SubElement( parent, self.__class__.__xml_name__ )
		id = sub( activity, 'Id', self.id )
		laps = [ l.as_xml( activity ) for l in self.laps ]
		training = self.training.as_xml( activity )
		creator = self.creator.as_xml( activity )
		return activity

@dataclass
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

# noinspection PyProtectedMember
def sub( parent: Element, name: str, value: Any ) -> Optional[SubElement]:
	if value is not None:
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

@dataclass
class TrainingCenterDatabase:

	__xml_name__ = 'TrainingCenterDatabase'

	# folders: Optional[Folders] = field( default=None )
	activities: List[Activity] = field( default_factory=list )
	# workouts: Optional[WorkoutList] = field( default=None )
	# courses: Optional[CourseList] = field( default=None )
	author: Optional[Author] = field( default=None )
	# extensions: Optional[Extensions] = field( default=None )

	def as_xml( self ):
		root = Element( self.__class__.__xml_name__ )
		activities_element = SubElement( root, 'Activities' )
		activities = [ a.as_xml( activities_element ) for a in self.activities ]
		author = self.author.as_xml( root ) if self.author else None
		return root

@importer( type=TCX_TYPE, activity_cls=Activity, recording=True )
class TCXImporter( XMLHandler ):

	def load_data( self, content: Union[bytes, str], **kwargs ) -> Any:
		return fromstring( content )

	def postprocess_data( self, raw: Any, **kwargs ) -> Any:
		root: ObjectifiedElement = raw.getroottree().getroot()
		for a in root.Activities.iterchildren( '{*}Activity' ):
			activity = Activity(
				id=find( a, 'Id' )
			)

			for l in a.iterchildren( '{*}Lap' ):
				activity.laps.append( Lap(
					start_time=parse_dt( l.get( 'StartTime' ) ),
					total_time_seconds=find( l, 'TotalTimeSeconds' ),
					distance_meters=find( l, 'DistanceMeters' ),
					maximum_speed=find( l, 'MaximumSpeed' ),
					calories=find( l, 'Calories' ),
					average_heart_rate_bpm=find( l, 'AverageHeartRateBpm.Value' ),
					maximum_heart_rate_bpm=find( l, 'MaximumHeartRateBpm.Value' ),
					cadence=find( l, 'Cadence' ),
					intensity=find( l, 'Intensity' ),
					trigger_method=find( l, 'TriggerMethod' ),
				) )

				for tp in l.Track.iterchildren( '{*}Trackpoint' ):
					activity.laps[-1].trackpoints.append( Trackpoint(
						time=find( tp, 'Time' ),
						latitude_degrees=find( tp, 'Position.LatitudeDegrees' ),
						longitude_degrees=find( tp, 'Position.LongitudeDegrees' ),
						altitude_meters=find( tp, 'AltitudeMeters' ),
						distance_meters=find( tp, 'DistanceMeters' ),
						heart_rate_bpm=find( tp, 'HeartRateBpm.Value' ),
						sensor_state=find( tp, 'SensorState' ),
						cadence=find( tp, 'Cadence' ),
					) )

			for t in a.iterchildren( '{*}Training' ):
				pass

			for c in a.iterchildren( '{*}Creator' ):
				creator_name = find( c, 'Name' )
				creator_unit_id = find( c, 'UnitId' )
				creator_product_id = find( c, 'ProductID' )
				creator_version_major = find( c, find( a, 'Creator.Version.VersionMajor' ) )
				creator_version_minor = find( c, find( a, 'Creator.Version.VersionMinor' ) )
				creator_build_major = find( c, find( a, 'Creator.Version.BuildMajor' ) )
				creator_build_minor = find( c, find( a, 'Creator.Version.BuildMinor' ) )

			return activity

	def preprocess_data( self, data: Any, **kwargs ) -> Any:
		return data

	def as_activity( self, resource: Resource ) -> Optional[TracsActivity]:
		tcx: Activity = resource.data
		return TracsActivity(
			distance=tcx.distance(),
			duration=tcx.duration(),
			time=tcx.time(),
			time_end=tcx.time_end(),
			localtime=tcx.time().astimezone( tzlocal() ),
			localtime_end=tcx.time_end().astimezone( tzlocal() ),
			uid=f'tcx:{tcx.time().strftime( "%y%m%d%H%M%S" )}',
		)

# helper

def find( element: ObjectifiedElement, sub_element: str ) -> Any:
	try:
		return ObjectPath( f'.{sub_element}' ).find( element ).pyval
	except AttributeError:
		return None

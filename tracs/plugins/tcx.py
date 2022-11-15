
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from logging import getLogger
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from dateutil.parser import parse as parse_dt
from dateutil.tz import tzlocal
from lxml.objectify import ObjectPath
from lxml.objectify import ObjectifiedElement

from .handlers import XMLHandler
from ..activity import Activity
from ..resources import Resource
from ..registry import document
from ..registry import importer

log = getLogger( __name__ )

TCX_TYPE = 'application/tcx+xml'

@dataclass
class TcxPoint:

	time: Union[datetime, str] = field( default=None )
	lat: float = field( default=None )
	lon: float = field( default=None )
	alt: float = field( default=None )
	dist: float = field( default=None )
	hr: float = field( default=None )
	sensor: float = field( default=None )

	def __post_init__( self ):
		self.time = parse_dt( self.time ) if type( self.time ) is str else self.time

@dataclass
class TcxLap:

	start_time: datetime = field( default=None )
	total_time: float = field( default=None )
	distance: float = field( default=None )
	max_speed: float = field( default=None )
	calories: int = field( default=None )
	heartrate: int = field( default=None )
	heartrate_max: int = field( default=None )
	cadence: int = field( default=None )

	points: List[TcxPoint] = field( default_factory=list )

	def __post_init__( self ):
		pass

	def time( self ) -> Optional[datetime]:
		return self.points[0].time if len( self.points ) > 0 else None

	def time_end( self ) -> Optional[datetime]:
		return self.points[-1].time if len( self.points ) > 0 else None

@dataclass
class TcxActivity:

	laps: List[TcxLap] = field( default_factory=list )

	def time( self ) -> Optional[datetime]:
		return self.laps[0].time() if len( self.laps ) > 0 else None

	def time_end( self ) -> Optional[datetime]:
		return self.laps[-1].time_end() if len( self.laps ) > 0 else None

@document( type=TCX_TYPE )
class TCXActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		tcx: TcxActivity = raw
		self.time = tcx.time()
		self.time_end = tcx.time_end()
		self.localtime = self.time.astimezone( tzlocal() )
		self.localtime_end = self.time_end.astimezone( tzlocal() )
		self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )

@importer( type=TCX_TYPE )
class TCXImporter( XMLHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=TCX_TYPE, activity_cls=TCXActivity )

	def postprocess_data( self, resource: Resource, **kwargs ) -> None:
		root: ObjectifiedElement = resource.raw.getroottree().getroot()

		for a in root.Activities.iterchildren( '{*}Activity' ):
			activity = TcxActivity()

			#sport = a.get( 'Sport' )
			#id = a.Id.text
			#creator_name = a.get( 'Lap', {} ).get( 'Name' )

			for l in a.iterchildren( '{*}Lap' ):
				activity.laps.append( TcxLap(
					start_time = parse_dt( l.get( 'StartTime' ) ),
					total_time = find( l, 'TotalTimeSeconds' ),
					distance = find( l, 'DistanceMeters' ),
					max_speed = find( l, 'MaximumSpeed' ),
					calories = find( l, 'Calories' ),
					heartrate = find( l, 'AverageHeartRateBpm.Value' ),
					heartrate_max = find( l, 'MaximumHeartRateBpm.Value' ),
					cadence = find( l, 'Cadence' ),
				) )

				for tp in l.Track.iterchildren( '{*}Trackpoint' ):
					activity.laps[-1].points.append( TcxPoint(
						time = find( tp, 'Time' ),
						lat = find( tp, 'Position.LatitudeDegrees' ),
						lon = find( tp, 'Position.LongitudeDegrees' ),
						alt = find( tp, 'AltitudeMeters' ),
						dist = find( tp, 'DistanceMeters' ),
						hr = find( tp, 'HeartRateBpm.Value' ),
						sensor = find( tp, 'SensorState' ),
					) )

			resource.raw = activity

# helper

def find( element: ObjectifiedElement, sub_element: str ) -> Any:
	try:
		return ObjectPath( f'.{sub_element}' ).find( element ).pyval
	except AttributeError:
		return None


from dataclasses import dataclass
from dataclasses import field
from dataclasses import InitVar
from datetime import datetime
from typing import List

from gpxpy.gpx import GPX

@dataclass
class Point:

	time: datetime = field( default=None )
	lat: float = field( default=None )
	lon: float = field( default=None )
	speed: float = field( default=None )

@dataclass
class Stream:

	points: List[Point] = field( default_factory=list )

	gpx: InitVar[GPX] = field( default=None )

	def __post_init__( self, gpx: GPX ):
		if gpx:
			gpx_points = [p for t in gpx.tracks for s in t.segments for p in s.points]
			self.points = [Point( p.time, p.latitude, p.longitude, p.speed ) for p in gpx_points ]

	@property
	def length( self ) -> int:
		return len( self.points )

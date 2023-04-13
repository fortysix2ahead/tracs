
from dataclasses import dataclass
from dataclasses import field
from dataclasses import InitVar
from datetime import datetime
from typing import List

from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
# from geojson import Point as GeojsonPoint
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrack
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXTrackSegment

from tracs.plugins.gpx import GPX_TYPE
from tracs.resources import Resource

# todo: no need to reinvent the wheel: chosse another point class here
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

	def as_geojson( self ) -> FeatureCollection:
		# return [ GeojsonPoint( (p.lon, p.lat) ) for p in self.points ] # todo: check that lat/lon order is correct
		segment = [ (p.lon, p.lat) for p in self.points ] # todo: check that lat/lon order is correct
		return FeatureCollection( [Feature( 'id_1', LineString( segment ), properties={} )] )

	def as_gpx_track( self ) -> GPXTrack:
		track = GPXTrack()
		segment = GPXTrackSegment( points = [GPXTrackPoint( time=p.time, latitude=p.lat, longitude=p.lon ) for p in self.points] )
		track.segments.append( segment )
		return track

	def as_gpx( self ) -> GPX:
		gpx = GPX()
		gpx.tracks.append( self.as_gpx_track() )
		return gpx

def as_streams( resources: List[Resource] ) -> List[Stream]:
	return [ Stream( gpx=r.raw ) for r in resources ]

def as_gpx( streams: List[Stream] ) -> GPX:
	gpx = GPX()
	gpx.tracks.extend( [s.as_gpx_track() for s in streams] )
	return gpx

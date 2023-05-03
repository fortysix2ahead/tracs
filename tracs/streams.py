
from csv import writer as csv_writer
from dataclasses import dataclass
from dataclasses import field
from dataclasses import InitVar
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Tuple
from typing import Optional

from geojson import dump as dump_geojson
from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
# from geojson import Point as GeojsonPoint
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrack
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXTrackSegment

from tracs.plugins.tcx import Trackpoint as TCXTrackPoint
from tracs.plugins.tcx import Lap as TCXLap
from tracs.resources import Resource

# todo: no need to reinvent the wheel: chosse another point class here
@dataclass
class Point:

	time: datetime = field( default=None )
	lat: float = field( default=None )
	lon: float = field( default=None )
	speed: float = field( default=None )
	alt: float = field( default=None )
	distance: float = field( default=None )
	hr: int = field( default=None )

	# init vars
	start: InitVar[datetime] = field( default=None )
	seconds: InitVar[int] = field( default=None )
	latlng: InitVar[Tuple[float, float]] = field( default=None )

	def __post_init__(self, start: datetime, seconds: int, latlng: int):
		if start and seconds:
			self.time = start + timedelta( seconds=seconds )
		if latlng:
			self.lat, self.lon = latlng

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

	def as_csv_list( self ) -> List[List[str]]:
		return [ [ str( p.lon ), str( p.lat ) ] for p in self.points ]

	def as_feature( self ) -> Feature:
		# return [ GeojsonPoint( (p.lon, p.lat) ) for p in self.points ] # todo: check that lat/lon order is correct
		segment = [ (p.lon, p.lat) for p in self.points ] # todo: check that lat/lon order is correct
		return Feature( 'id_1', LineString( segment ), properties={} )

	def as_gpx_track( self ) -> GPXTrack:
		track = GPXTrack()
		segment = GPXTrackSegment( points = [GPXTrackPoint( time=p.time, latitude=p.lat, longitude=p.lon, elevation=p.alt, speed=p.speed ) for p in self.points] )
		track.segments.append( segment )
		return track

	def as_gpx( self ) -> GPX:
		gpx = GPX()
		gpx.tracks.append( self.as_gpx_track() )
		return gpx

	def as_tcx_lap( self ) -> TCXLap:
		points = [ TCXTrackPoint( time=p.time, lat=p.lat, lon=p.lon, alt=p.alt, dist=p.distance, hr=p.hr ) for p in self.points ]
		return TCXLap( points = points )

def as_streams( resources: List[Resource] ) -> List[Stream]:
	return [ Stream( gpx=r.raw ) for r in resources ]

def as_csv( streams: List[Stream] ) -> str:
	csv = [ ['longitude', 'latitude'], *[line for s in streams for line in s.as_csv_list()]]
	io = StringIO()
	writer = csv_writer( io, delimiter=';', lineterminator='\n' )
	writer.writerows( csv )
	return io.getvalue()

def as_gpx( streams: List[Stream] ) -> GPX:
	gpx = GPX()
	gpx.tracks.extend( [s.as_gpx_track() for s in streams] )
	return gpx

def as_feature_collection( streams: List[Stream] ) -> FeatureCollection:
	return FeatureCollection( [ s.as_feature() for s in streams ] )

def as_str( resources: List[Resource], fmt: str ) -> Optional[str]:
	if fmt == 'csv':
		return as_csv( as_streams( resources ) )
	elif fmt == 'gpx':
		return as_gpx( as_streams( resources ) ).to_xml( prettyprint=False )
	elif fmt == 'geojson':
		io = StringIO()
		dump_geojson( as_feature_collection( as_streams( resources ) ), io )
		return io.getvalue()
	else:
		return None

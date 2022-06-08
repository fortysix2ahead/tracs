
from logging import getLogger

from csv import writer as csv_writer
from typing import Iterable

from geojson import dump as dump_geojson
from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
from gpxpy.gpx import GPX
from pathlib import Path

from .activity import Activity
from .config import ApplicationConfig as cfg
from .db import ActivityDb
from .gpx import read_gpx

log = getLogger( __name__ )

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

def reimport_activities( activities: Iterable[Activity], db: ActivityDb, force: bool = False ):
	for a in activities:
		if a.is_group:
			for doc_id in a.group_for:
				child = db.get( doc_id=doc_id )
				child.init_fields( force=force )
				db.update( child )
			a.init_fields( sources=[db.get( doc_id=doc_id ) for doc_id in a.group_for], force=force )
		else:
			a.init_fields( force=force )
		db.update( a )

def export_csv( activities: Iterable[Activity], output: Path ):
	csv = [['longitude', 'latitude']]

	merged_gpx = _merge_gpx( activities )

	for t in merged_gpx.tracks:
		for s in t.segments:
			for p in s.points:
				csv.append( [ p.longitude, p.latitude ] )

	if not output.is_absolute():
		output = Path( Path.cwd(), output )

	if not cfg['pretend'].get():
		with open( output, 'w', encoding='utf8' ) as f:
			cw = csv_writer( f, delimiter=';', lineterminator='\n' )
			cw.writerows( csv )
			log.debug( f'wrote merged csv to {str( output )}' )

def export_geojson( activities: Iterable[Activity], output: Path ):
	features = []
	merged_gpx = _merge_gpx( activities )

	for t in merged_gpx.tracks:
		for s in t.segments:
			segment = [(p.longitude, p.latitude) for p in s.points]
			# example: LineString( [ (8.919, 44.4074), (8.923, 44.4075) ] ) -> takes a list of tuples
			geometry = LineString( segment )
			# geometry = MultiLineString( [tuple( segment )] )  # that's messy ... :-(
			properties = {
			#	'time': r.time,
			}
			features.append( Feature( '', geometry, properties ) )

	if not cfg['pretend'].get():
		with open( output, 'w', encoding='utf8' ) as f:
			dump_geojson( FeatureCollection( features ), f )
			log.debug( f'wrote merged geojson to {str( output )}' )

def export_kml( activities, output ):
	pass

def export_gpx( activities: Iterable[Activity], output: Path ):
	#pf = perf_counter()
	merged_gpx = _merge_gpx( activities )

	if not output.is_absolute():
		output = Path( Path.cwd(), output )

	if not cfg['pretend'].get():
		with open( output, 'w', encoding='utf8' ) as f:
			f.write( merged_gpx.to_xml() )
			log.debug( f'wrote merged gpx to {str( output )}' )

	#log.info( f'reading gpx files took {perf_counter() - pf}' )

def export_shp( activities, output: str = None ):
	pass

def _merge_gpx( activities: Iterable[Activity] ) -> GPX:
	merged_gpx = GPX()
	for a in activities:
		gpx = _read_gpx( a )
		merged_gpx.tracks.extend( gpx.tracks if gpx else [] )

	log.debug( f'merged gpx contains {merged_gpx.get_points_no()} points' )

	return merged_gpx

def _read_gpx( a: Activity ) -> GPX:
	gpx = None

	for ea in a.refs():
		gpx_path = ea.service.path_for( ea, 'gpx' )
		if gpx_path.exists():
			gpx = read_gpx( gpx_path )
			log.debug( f'read {gpx.get_points_no()} points from {gpx_path}' )
			break

	return gpx


from logging import getLogger

from copy import deepcopy
from csv import writer as csv_writer
from os import getcwd
from os import system
from typing import Iterable
from typing import List
from typing import Optional

from geojson import dump as dump_geojson
from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
from gpxpy.gpx import GPX
from pathlib import Path

from rich.console import Console

from .activity import Activity
from .activity import Resource
from .config import ApplicationConfig as cfg
from .config import ApplicationContext
from .dataclasses import as_dict
from .db import ActivityDb
from .gpx import read_gpx
from .plugins import Registry
from .plugins.handlers import GPX_TYPE
from .plugins.handlers import TCX_TYPE
from .plugins.polar import PolarActivity
from .service import Service
from .ui import diff_table
from .ui import InstantConfirm as Confirm

log = getLogger( __name__ )

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

def import_activities( ctx: Optional[ApplicationContext], sources: List[str], importer: str ):
	for src in list( sources ):
		path = Path( src )
		if not path.is_absolute():
			path = Path( getcwd(), src )

		Registry.services.get( 'local' ).fetch( force=False, path=path )

def open_activities( activities: List[Activity], db: ActivityDb ) -> None:
	if len( activities ) > 0:
		activity = activities[0]
		if len( activities ) > 1:
			log.warning( 'opening more than one activity at once is not yet supported, only opening the first ...' )

		resource_type = 'gpx' # todo: make this configurable

		# todo: this is just a PoC!
		for uid in activity.uids:
			resources = db.find_resources( uid )
			for r in resources:
				if r.type == resource_type:
					service, raw_id = r.uid.split( ':' )
					path = Registry.services.get( service ).path_for( PolarActivity( raw_id=raw_id ) )
					path = Path( path, r.path )
					system( 'open ' + path.as_posix() )

		# os.system( "open " + shlex.quote( filename ) )  # MacOS/X
		# os.system( "start " + filename )  # windows

def reimport_activities( ctx: ApplicationContext, activities: List[Activity], include_recordings: bool = False, force: bool = False ):
	log.debug( f'reimporting {len( activities )} activities, with force={force}' )

	for activity in activities:
		activity_source = deepcopy( activity )
		for uid in activity.uids:
			resources = ctx.db.find_resources( uid )
			# first iteration: import from raw data only
			for r in resources:
				if not r.type in [ GPX_TYPE, TCX_TYPE ]:
					log.debug( f'importing resource of type {r}' )
					imported_activity = load_resource( r )
					activity.init_from( other=imported_activity )

			# second iteration import from recording when flag is set
			for r in resources:
				if include_recordings and r.type in [ GPX_TYPE, TCX_TYPE ]:
					log.debug( f'importing resource of type {r}' )
					imported_activity = load_resource( r )
					activity.init_from( other=imported_activity )

		if force or _confirm_init( activity_source, activity, ctx.console ):
			ctx.db.update( activity )

def load_resource( resource: Resource ) -> Optional[Activity]:
	importers = Registry.importers_for( resource.type )
	path = Service.path_for_resource( resource )

	for i in importers:
		if activity := i.load( path = path ):
			return activity

	log.error( f'no importer found for resource type {resource.type}' )

def _confirm_init( source: Activity, target: Activity, console: Console ) -> bool:
	table = diff_table( as_dict( source, remove_protected=True ), as_dict( target, remove_protected=True ), header=('Field', 'Old Value', 'New Value') )
	if len( table.rows ) > 0:
		console.print( table )
		answer = Confirm.ask( f'Would you like to reimport activity {source.uid}?', default=False )
	else:
		log.info( f'no difference found during reimport of activity {source.uid}, skipping reimport' )
		answer = False
	return answer

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

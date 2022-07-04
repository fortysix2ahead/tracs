
from logging import getLogger

from csv import writer as csv_writer
from typing import Any
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
from .db import ActivityDb
from .gpx import read_gpx
from .plugins import Registry
from .plugins.groups import ActivityGroup
from .ui import diff_table
from .ui import InstantConfirm as Confirm

log = getLogger( __name__ )

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

def reimport_activities( ctx: Optional[ApplicationContext], activities: List[Activity], db: ActivityDb, from_raw: bool = True, force: bool = False ):
	log.debug( f'reimporting {len( activities )} activities, with force={force}' )

	for a in activities:
		if type( a ) == ActivityGroup:
			children = []
			for doc_id in a.group_ids:
				child = db.get( doc_id=doc_id )
				children.append( _reimport_nongroup_activity( child, from_raw ) )
			new_activity = _reimport_group_activity( a, children, from_raw )
			if force or _confirm_init( a, new_activity, ctx.console if ctx else Console() ):
				a.init_from( other=new_activity )

		else:
			new_activity = _reimport_nongroup_activity( a, from_raw )
			if force or _confirm_init( a, new_activity, ctx.console if ctx else Console() ):
				a.init_from( other=new_activity )

		#db.update( a )

def _reimport_group_activity( parent: Activity, children: List[Activity], from_raw ) -> Activity:
	return ActivityGroup( group=children )

def _reimport_nongroup_activity( a: Activity, from_raw: bool ) -> Activity:
	resources = [_find_resource( a, 'raw' )] if from_raw else a.resources
	new_activity = a.__class__()

	for r in resources:
		resource_data = _load_resource( a, r )
		if isinstance( resource_data, Activity ):
			new_activity.init_from( other=resource_data )
		else:
			new_activity.init_from( raw=resource_data )

	return new_activity

def _find_resource( activity: Activity, resource_type: str ) -> Optional[Resource]:
	for r in activity.resources:
		if r.type == resource_type:
			return r
	return None

#def _load_resources( activity: Activity ) -> List:
#	return [_load_resource( activity, r ) for r in activity.resources]

def _load_resource( activity: Activity, resource: Resource ) -> Any:
	handler_cls = Registry.document_handlers.get( resource.type ) or Registry.document_handlers.get( resource.path.rsplit( '.', 1 )[1] )
	handler = handler_cls()
	path = Path( Registry.services[activity.classifier].path_for( activity ), resource.path )
	try:
		return handler.load( path )
	except:
		log.error( f'no handler found for resource type {resource.type}' )

def _confirm_init( source: Activity, target: Activity, console: Console ) -> bool:
	console.print( diff_table( source.asdict(), target.asdict() ) )
	answer = Confirm.ask( f'Would you like to reimport activity {source.uid}?', default=False )
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

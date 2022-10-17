from datetime import datetime
from datetime import time
from datetime import timedelta
from logging import getLogger

from copy import deepcopy
from csv import writer as csv_writer
from os import system
from re import match
from typing import Iterable
from typing import List
from typing import Optional
from urllib.parse import urlparse as parse_url

from dateutil.tz import gettz
from geojson import dump as dump_geojson
from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
from gpxpy.gpx import GPX
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from tzlocal import get_localzone_name

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
from .service import Service
from .ui import diff_table

log = getLogger( __name__ )

TAG_OFFSET_CORRECTION = 'offset'
TAG_TIMEZONE_CORRECTION = 'timezone'

MAXIMUM_OPEN = 8

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

#def import_activities( ctx: Optional[ApplicationContext], sources: List[str], importer: str, as_one: bool = False, move: bool = False, **kwargs ):
def import_activities( ctx: Optional[ApplicationContext], sources: List[str], **kwargs ):
	# use all registered services if nothing is provided
	sources = sources or Registry.service_names()

	for src in list( sources ):
		if src in Registry.services.keys():
			log.info( f'importing from service {src}' )
			Registry.services.get( src ).import_activities( ctx=ctx, force=ctx.force, pretend=ctx.pretend, **kwargs )

		elif ( m := match( '^([a-z]+):(\d+)$', src ) ) and m.groups()[0] in Registry.services.keys():
			Registry.services.get( m.groups()[0] ).import_activities( ctx=ctx, uid=src, force=ctx.force, pretend=ctx.pretend, **kwargs )

		elif ( path := Path( src ).absolute() ) and path.exists():
			log.info( f'importing from path {path}' )
			kwargs['skip_download'] = True
			kwargs['path'] = path
			Registry.services.get( 'local' ).import_activities( ctx=ctx, force=ctx.force, pretend=ctx.pretend, **kwargs )

		elif url := parse_url( src ):
			raise NotImplementedError

		else:
			log.error( f'unable to import from {src}' )

def open_activities( activities: List[Activity], db: ActivityDb ) -> None:
	if len( activities ) > MAXIMUM_OPEN:
		log.warning( f'limit of number of activities to open is {MAXIMUM_OPEN}, ignoring the rest of provided {len( activities )} activities' )
		activities = activities[:MAXIMUM_OPEN]

	resource_type = GPX_TYPE # todo: make this configurable

	paths = []

	for a in activities:
		for uid in a.uids:
			resources = db.find_resources( uid )
			for r in resources:
				if r.type == resource_type:
					paths.append( Service.path_for_resource( r ) )
					break

	paths = [ str( p ) for p in paths ]
	system( 'open ' + ' '.join( paths ) )

		# os.system( "open " + shlex.quote( filename ) )  # MacOS/X
		# os.system( "start " + filename )  # windows

def reimport_activities( ctx: ApplicationContext, activities: List[Activity], include_recordings: bool = False, offset: str = None, timezone: str = None, force: bool = False ):
	log.debug( f'reimporting {len( activities )} activities, with force={force}' )

	try:
		if offset.startswith( '-' ):
			offset = time.fromisoformat( offset.lstrip( '-' ) )
			offset_delta = timedelta( hours=-offset.hour, minutes=-offset.minute, seconds=-offset.second, microseconds=-offset.microsecond )
		else:
			offset = time.fromisoformat( offset.lstrip( '+' ) )
			offset_delta = timedelta( hours=offset.hour, minutes=offset.minute, seconds=offset.second, microseconds=offset.microsecond )

		timezone = gettz( timezone ) if timezone else None

	except (AttributeError, ValueError):
		log.error( 'unable to parse offset/timezone', exc_info=True )
		offset_delta = None
		timezone = None

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

		if offset_delta:
			activity.time = activity.time + offset_delta
			activity.tag( TAG_OFFSET_CORRECTION )

		if timezone:
			activity.timezone = timezone.tzname( datetime.utcnow() )
			activity.localtime = activity.time.astimezone( timezone )
			activity.tag( TAG_TIMEZONE_CORRECTION )
		else:
			activity.timezone = get_localzone_name()
			activity.localtime = activity.time.astimezone( gettz( activity.timezone ) )

		if force or _confirm_init( activity_source, activity, ctx.console ):
			ctx.db.update( activity )

def load_all_resources( db: ActivityDb, activity: Activity ) -> None:
	all_resources = []
	for uid in activity.uids:
		all_resources.extend( db.find_resources( uid ) )

	activity.resources = all_resources

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

def export_activities( activities: Iterable[Activity], force: bool = False, pretend: bool = False, **kwargs ):
	pass

def export_resources( resources: Iterable[Activity], force: bool = False, pretend: bool = False, **kwargs ):
	pass

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

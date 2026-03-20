from datetime import datetime, time, timedelta
from logging import getLogger
from os import system
from pathlib import Path
from shlex import quote
from typing import List, Optional, Tuple, Union

from datetimerange import DateTimeRange
from dateutil.tz import gettz, UTC
from fs.errors import ResourceNotFound
from rich.prompt import Confirm
from tzlocal import get_localzone_name

from tracs.activity import Activities, Activity, ActivityTypes
from tracs.constants import CFG_FROM_TAKEOUTS, UNSET
from tracs.errors import ImportException
from tracs.protocols import ApplicationContext
from tracs.db import ActivityDb
from tracs.plugins.gpx import GPX_TYPE
from tracs.pluginmgr import Registry
from tracs.resources import Resource
from tracs.service import Service
from tracs.streams import as_str
from tracs.ui import diff_table
from tracs.utils import fspath

log = getLogger( __name__ )

TAG_OFFSET_CORRECTION = 'offset'
TAG_TIMEZONE_CORRECTION = 'timezone'

MAXIMUM_OPEN = 8

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

# 		import_all=import_all,
# 		classifier=classifier,
# 		move=move,
# 		from_source=from_source,
# 		type=type,

def import_activities( ctx: ApplicationContext,
                       import_all: bool = False, classifier: str = None, move: bool = False,
                       from_source: str = None, services: Tuple[str, ...] = None, type: str = None ) -> Activities:
	# setup
	imported = Activities()

	# input validation

	if type and type not in ActivityTypes.names():
		raise ImportException( f'cannot use unknown activity type "{type}" during import, use the command "types" to learn what types exist' )

	if from_source and from_source != UNSET and len( services ) > 1:
		raise ImportException( f'import from multiple sources cannot be used in conjunction with -s and external files/directories' )

	if not all( [ ctx.service_mgr.get( s ) is not None for s in services ] ):
		raise ImportException( f'list of services to import from ({services}) contains an invalid entry (service does not exist)' )

	if from_source and from_source != UNSET and len( services ) == 0:
		log.info( 'import source, but no service to use provided, attempting to use "local" for import' )
		services = ( 'local', )

	# import range
	first_year = ctx.config['import'].first_year
	days_range = ctx.config['import'].range

	if import_all:
		range_from = datetime( first_year, 1, 1, tzinfo=UTC )
	else:
		range_from = datetime.now( UTC ) - timedelta( days = days_range )
	range_to = datetime.now( UTC ) + timedelta( days=1 )

	# actual import
	for service in [ ctx.service_mgr.get( s ) for s in services ]:

		if from_source and from_source == UNSET:
			src_fs, src_file = ctx.takeout_fs( service.name ), None
		elif from_source:
			src_fs, src_file = fspath( from_source )
		else:
			src_fs, src_file = None, None

		imported.extend(
			service.import_activities( ctx.force, ctx.pretend, src_fs=src_fs, src_file=src_file, classifier=classifier,
			                           type=type, range_from=range_from, range_to=range_to )
		)

	return imported

def open_activities( ctx: ApplicationContext, activities: List[Activity] ) -> None:
	if len( activities ) > MAXIMUM_OPEN:
		log.warning( f'limit of number of activities to open is {MAXIMUM_OPEN}, ignoring the rest of provided {len( activities )} activities' )
		activities = activities[:MAXIMUM_OPEN]

	resource_type = GPX_TYPE # todo: make this configurable

	resources = [ a.resource_of_type( resource_type ) for a in activities ]
	paths = [ quote( p ) for p in [ ctx.db_fs.getsyspath( r.path ) for r in resources ] if p is not None ]

	if paths:
		system( 'open ' + ' '.join( paths ) )

		# os.system( "open " + shlex.quote( filename ) )  # MacOS/X
		# os.system( "start " + filename )  # windows

def reimport_activities(
		activities: List[Activity],
		include_recordings: bool = False,
		from_remote: bool = False,
		strategy: str = None,
		offset: str = None,
		timezone: str = None,
		ignore_fields: List[str] = None,
		ctx: ApplicationContext = None ):

	log.debug( f'reimporting {len( activities )} activities, with force={ctx.force}' )

	ignore_fields = ignore_fields if ignore_fields is not None else []

	try:
		if offset.startswith( '-' ):
			offset = time.fromisoformat( offset.lstrip( '-' ) )
			offset_delta = timedelta( hours=-offset.hour, minutes=-offset.minute, seconds=-offset.second, microseconds=-offset.microsecond )
		else:
			offset = time.fromisoformat( offset.lstrip( '+' ) )
			offset_delta = timedelta( hours=offset.hour, minutes=offset.minute, seconds=offset.second, microseconds=offset.microsecond )

		timezone = gettz( timezone ) if timezone else None

	except (AttributeError, ValueError):
		log.debug( 'unable to parse offset/timezone', exc_info=True )
		offset_delta = None
		timezone = None

	# when non-interactive (a.k.a. force) show a progress bar
	if ctx.force:
		ctx.start( f'reimporting activity data', total=len( activities ) )

	for a in activities:
		ctx.advance( f'{a.uids}' )

		all_resources = ctx.db.find_all_resources( a.refs() )
		resources = [r for r in all_resources if ctx.registry.resource_types.get( r.name ).summary]
		resources.extend( [r for r in all_resources if include_recordings and ctx.registry.resource_types.get( r.name ).recording] )
		src_activities = [ a2 for r in resources if ( a2:= Service.as_activity( r ) ) ]

		new_activity = Activity.group_of( *src_activities, ignored_fields=ignore_fields )

		if offset_delta:
			new_activity.starttime = new_activity.starttime + offset_delta
			new_activity.tag( TAG_OFFSET_CORRECTION )

		if timezone:
			new_activity.timezone = timezone.tzname( datetime.utcnow() )
			new_activity.starttime_local = new_activity.starttime.astimezone( timezone )
			new_activity.tag( TAG_TIMEZONE_CORRECTION )
		else:
			new_activity.timezone = get_localzone_name()
			new_activity.starttime_local = new_activity.starttime.astimezone( gettz( a.timezone ) )

		if ctx.force or _confirm_init( a, new_activity, ignore_fields, ctx ):
			ctx.db.upsert_activity( new_activity )

	ctx.db.commit()
	ctx.complete( 'done' )

def load_all_resources( db: ActivityDb, activity: Activity ) -> List[Resource]:
	resources = []
	for uid in activity.uids:
		resources.extend( db.find_resources( uid ) )
	return resources

def load_resource( resource: Resource, as_activity: bool = False, update_raw: bool = False ) -> Optional[Union[Resource, Activity]]:
	importers = Registry.importers_for( resource.type )
	path = Service.path_for_resource( resource )

	for i in importers:
		if as_activity:
			if activity := i.load_as_activity( path=path ):
				return activity
		else:
			if loaded_resource := i.load( path=path ):
				if update_raw:
					resource.raw = loaded_resource.raw
				return loaded_resource

	log.error( f'unable to load resource {resource.uid}?{resource.path}, no importer found for resource type {resource.type}' )

def _confirm_init( source: Activity, target: Activity, ignore: List[str], ctx: ApplicationContext ) -> bool:
	src_dict, target_dict = source.to_dict(), target.to_dict()
	# don't display ignored fields
	src_dict = { k: v for k, v in src_dict.items() if k not in ignore }
	target_dict = { k: v for k, v in target_dict.items() if k not in ignore }

	table = diff_table( src_dict, target_dict, header=('Field', 'Old Value', 'New Value'), sort_entries=True )
	if len( table.rows ) > 0:
		ctx.console.print( table )
		answer = Confirm.ask( f'Would you like to reimport activity {source.id} \[{", ".join( source.uids)}]?', default=False )
	else:
		ctx.console.print( f'no difference found during reimport of activity {source.id} \[{", ".join( source.uids)}], skipping reimport' )
		answer = False
	return answer

def export_activities( ctx: ApplicationContext, activities: List[Activity], fmt: str = None, output: str = None, aggregate: bool = True, overlay: bool = False, **kwargs ):
	if fmt not in [ 'csv', 'gpx', 'geojson' ]:
		ctx.console.print( f'unable to export, unsupported format {fmt}' )
		return

	importer = Registry.importer_for( GPX_TYPE )
	resources = [ctx.db.get_resource_of_type( a.uids, GPX_TYPE ) for a in activities]
	resources = [ importer.load( Service.path_for_resource( r ) ) for r in resources ]

	path = Path( ctx.var_path, f'export_{datetime.now().strftime( "%Y%m%d_%H%M%S" )}.{fmt}' )  # todo: created proper name
	path.write_text( as_str( resources, fmt ) )
	ctx.console.print( f'successfully exported to {str( path )}' )

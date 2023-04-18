from datetime import datetime
from datetime import time
from datetime import timedelta
from logging import getLogger
from os import system
from pathlib import Path
from re import compile
from typing import cast
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import urlparse as parse_url

from dateutil.tz import gettz
from rich.prompt import Confirm
from tzlocal import get_localzone_name

from .activity import Activity
from .config import ApplicationContext
from .db import ActivityDb
from .plugins.gpx import GPX_TYPE
from .plugins.local import SERVICE_NAME as LOCAL_SERVICE_NAME
from .registry import Registry
from .resources import Resource
from .resources import ResourceType
from .resources import UID
from .service import Service
from .streams import as_str
from .ui import diff_table

log = getLogger( __name__ )

TAG_OFFSET_CORRECTION = 'offset'
TAG_TIMEZONE_CORRECTION = 'timezone'

DEFAULT_IMPORTER = 'auto'

MAXIMUM_OPEN = 8

# kepler: https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map#geojson
# also nice: https://github.com/luka1199/geo-heatmap

uid_pattern = compile( f'^({"|".join( Registry.service_names() )}):(\d+)$' )

def import_activities( ctx: Optional[ApplicationContext], importer: Optional[str], sources: List[str], **kwargs ):
	# use all registered services if nothing is provided
	# services = [ s for i in importers if ( s := Registry.services.get( i ) ) ]

	sources = sources or Registry.service_names()

	for src in sources:
		uid = UID( src )

		if uid.denotes_service() and (service := Registry.services.get( src )):
			log.debug( f'importing from service {src}' )
			service.import_activities( ctx=ctx, force=ctx.force, pretend=ctx.pretend, **kwargs )

		elif uid.denotes_activity() and (service := Registry.service_for( uid.classifier )):
			service.import_activities( ctx=ctx, force=ctx.force, pretend=ctx.pretend, uids=[src], **kwargs )

		elif uid.denotes_resource() and (service := Registry.service_for( uid.classifier )):
			raise NotImplementedError

		else:
			# try to use src as path
			try:
				path = Path( Path.cwd(), src ).absolute().resolve()
				if path.exists():
					log.debug( f'attempting to import from path {path}' )
					kwargs['skip_download'] = False
					kwargs['path'] = path

					s = Registry.services.get( importer, Registry.services.get( LOCAL_SERVICE_NAME ) )
					s.import_activities( ctx=ctx, force=ctx.force, pretend=ctx.pretend, **kwargs )
			except RuntimeError:
				log.error( 'unable to import from path', exc_info=True )

				try:
					url = parse_url( src )
				except:
					raise NotImplementedError

def open_activities( activities: List[Activity], db: ActivityDb ) -> None:
	if len( activities ) > MAXIMUM_OPEN:
		log.warning( f'limit of number of activities to open is {MAXIMUM_OPEN}, ignoring the rest of provided {len( activities )} activities' )
		activities = activities[:MAXIMUM_OPEN]

	resource_type = GPX_TYPE # todo: make this configurable

	paths = []

	for a in activities:
		if resources := db.find_resources_of_type( resource_type, a ):
			paths.append( Service.path_for_resource( resources[0] ) )

	paths = [ str( p ) for p in paths ]
	system( 'open ' + ' '.join( paths ) )

		# os.system( "open " + shlex.quote( filename ) )  # MacOS/X
		# os.system( "start " + filename )  # windows

def reimport_activities( activities: List[Activity], include_recordings: bool = False, strategy: str = None, offset: str = None, timezone: str = None, ignore_fields: List[str] = None, ctx: ApplicationContext = None ):
	force = ctx.force
	ignore_fields = ignore_fields if ignore_fields is not None else []
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
		log.debug( 'unable to parse offset/timezone', exc_info=True )
		offset_delta = None
		timezone = None

	# when non-interactive (a.k.a. force) show a progress bar
	if force:
		ctx.start( f'reimporting activity data', total=len( activities ) )

	for a in activities:
		ctx.advance( f'{a.uids}' )

		all_resources = ctx.db.find_all_resources( a.uids )
		resources = [ r for r in all_resources if Registry.resource_types.get( r.type ).summary ]
		resources.extend( [ r for r in all_resources if include_recordings and Registry.resource_types.get( r.type ).recording ] )
		src_activities = [ a2 for r in resources if ( a2:= Service.as_activity( r ) ) ]

		new_activity = a.union( others=src_activities, copy=True, ignore=ignore_fields )

		if offset_delta:
			new_activity.time = new_activity.time + offset_delta
			new_activity.tag( TAG_OFFSET_CORRECTION )

		if timezone:
			new_activity.timezone = timezone.tzname( datetime.utcnow() )
			new_activity.localtime = new_activity.time.astimezone( timezone )
			new_activity.tag( TAG_TIMEZONE_CORRECTION )
		else:
			new_activity.timezone = get_localzone_name()
			new_activity.localtime = new_activity.time.astimezone( gettz( a.timezone ) )

		if force or _confirm_init( a, new_activity, ignore_fields, ctx ):
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
	src_dict = ctx.db.factory.dump( source, Activity )
	target_dict = ctx.db.factory.dump( target, Activity )
	# don't display ignored fields
	src_dict = { k: v for k, v in src_dict.items() if k not in ignore }
	target_dict = { k: v for k, v in target_dict.items() if k not in ignore }

	table = diff_table( src_dict, target_dict, header=('Field', 'Old Value', 'New Value') )
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

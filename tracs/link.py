from logging import getLogger
from pathlib import Path
from re import compile as rxcompile
from typing import List

from tracs.activity import Activity
from tracs.config import ApplicationContext
from tracs.plugins.gpx import GPX_TYPE
from tracs.service import Service
from tracs.resources import Resource

log = getLogger( __name__ )

PATTERN = rxcompile( r'[^0-9a-zA-ZäöüßÄÖÜ -.\[\]\s]+' ) # todo: improve regex

def link_activities( ctx: ApplicationContext, activities: List[Activity] ) -> None:
	ctx.start( 'creating links for activities', len( activities ) )

	for a in activities:
		ctx.advance( str( a.uids ) )
		gpx: Resource = ctx.db.get_resource_of_type( a.uids, GPX_TYPE )
		if gpx:
			src = Service.path_for_resource( resource=gpx )
			target = link_for( ctx, a, gpx )

			if not src or not src.exists() or src.is_dir():
				log.debug( f"cannot link resource {gpx.uid}?{gpx.path}: source path {src} does not exist or is not a file" )
				continue

			if not ctx.pretend:
				target.parent.mkdir( parents=True, exist_ok=True )
				target.unlink( missing_ok=True )
				target.symlink_to( src )

			log.debug( f"linked resource {gpx.uid}?{gpx.path}: {src} -> {target}" )

	ctx.complete( 'done' )

def link_for( ctx: ApplicationContext, activity: Activity, resource: Resource ) -> Path:
	ts = activity.time.strftime( '%Y%m%d%H%M%S' )
	if activity.name:
		name = f'{activity.name} [{ts[8:14]}].gpx'
	else:
		name = f'{activity.type.display_name} [{ts[8:14]}].gpx' if activity.type else f'activity [{ts[8:14]}].gpx'
	name = PATTERN.sub( '', name ) # todo: find a better way to create names
	return Path( ctx.lib_dir_path, ts[0:4], ts[4:6], ts[6:8], name )

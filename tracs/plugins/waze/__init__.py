from datetime import timedelta
from logging import getLogger
from pathlib import Path
from typing import Callable, cast, ClassVar, Optional, Tuple, Union

from dateutil.tz import tzlocal
from fs.base import FS
from fs.path import dirname, frombase, parts, relpath
from gpxpy.gpx import GPX, GPXTrack, GPXTrackPoint, GPXTrackSegment
from more_itertools import unique
from more_itertools.more import first, last

from tracs.activity import Activities
from tracs.pluginmgr import resourcetype, service
from tracs.plugins.gpx import GPX_TYPE, GPXImporter
from tracs.plugins.waze.constants import *
from tracs.plugins.waze.io import WazeAccountActivityImporter, WazeAccountInfoImporter, WazeImporter
from tracs.plugins.waze.model import *
from tracs.resources import Resource, ResourceType
from tracs.service import date_id_to_path, Service

log = getLogger( __name__ )

@resourcetype
def bikecitizens_resource_types() -> List[ResourceType]:
	return [
		ResourceType( name=WAZE_TYPE, summary=True ),
		ResourceType( name=WAZE_ACCOUNT_ACTIVITY_TYPE ),
		ResourceType( name=WAZE_ACCOUNT_INFO_TYPE ),
	]

@service
class Waze( Service ):

	SERVICE_NAME: ClassVar[str] = SERVICE_NAME

	def __init__( self, **kwargs ):
		super().__init__( **kwargs )
		# super().__init__( **{ **{'name': SERVICE_NAME, 'display_name': DISPLAY_NAME}, **kwargs } )

		self._takeout_importer: WazeAccountActivityImporter = WazeAccountActivityImporter()
		self._info_importer: WazeAccountInfoImporter = WazeAccountInfoImporter()
		self._drive_importer: WazeImporter = WazeImporter()
		self._gpx_importer: GPXImporter = GPXImporter()

		self._takeout_importer.field_size_limit = kwargs.get( 'field_size_limit' ) or DEFAULT_FIELD_SIZE_LIMIT

		self._logged_in = True

	@property
	def field_size_limit( self ) -> int:
		return self._takeout_importer.field_size_limit

	@field_size_limit.setter
	def field_size_limit( self, field_size_limit: int ) -> None:
		if hasattr( self, '_takeout_importer' ):
			self._takeout_importer.field_size_limit = field_size_limit

	def path_for_id( self, local_id: Union[int, str], base_path: Optional[str] = None, user_id: Optional[str] = None,
	                 resource_path: Optional[str] = None, as_path: bool = False, id_to_path: Callable = None ) -> Union[Path, str]:
		return super().path_for_id( local_id, base_path, user_id, resource_path, as_path, date_id_to_path )

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return None

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		return None

	# noinspection PyMethodMayBeStatic
	def supports_fs_import( self, fs: FS | None, path: str | None ) -> bool:
		return any ( [ f for f in fs.walk.files( '/', filter=[ ACTIVITY_FILE ] ) ] )

	def import_from_fs( self, src_fs: FS, dst_fs: FS, **kwargs ) -> Activities:
		log.info( f'searching {src_fs.getsyspath( "" )} for Waze takeout files' )

		# check if activity files are already known
		activity_files = sorted( [ f for f in src_fs.walk.files( '/', filter=[ ACTIVITY_FILE ] ) ] )
		known_files = list( unique( [ r.source for r in self.db.resources if r.source is not None ] ) )
		known_files = [ frombase( self.name, kf ) for kf in known_files if parts( relpath( kf ) )[1] == self.name ]

		# logging
		for kn in known_files:
			log.debug( f'skipping import from already known takeout file {kn}' )
		log.info( f'found {len( activity_files )} takeout file(s) from which {len( known_files )} are already known (data has already been imported from)' )

		if not self.ctx.force:
			activity_files = [ af for af in activity_files if af not in known_files ]

		log.info( f'found {len( activity_files )} unknown takeout file(s) which are used for import' )
		# self.ctx.total( len( activity_files ) )

		activities = Activities()

		for file in activity_files:
			log.info( f'importing activities from Waze takeout in {file}' )
			# self.ctx.advance( f'{file}' )

			takeout_resource = self._takeout_importer.load( fs=src_fs, path=file )
			account_activity = cast( AccountActivity, takeout_resource.data )
			for ld in account_activity.location_details:
				# ignore drives without timestamps, see issue #74
				if not all( p.time for p in ld.as_point_list() ):
					continue

				uid = f'{self.name}:{ld.id()}'
				path = self.svc_path_for_id( ld.id(), f'{ld.id()}.txt' )
				source = f'{self.name}{file}'

				if self.ctx.force or not self.db.contains_resource( uid, path ):
					# create and write summary
					summary = Resource(
						content=ld.coordinates.encode( 'UTF-8' ),
						path=path,
						raw=ld, # this allows to skip parsing again
						type=WAZE_TYPE,
					)

					# create and write gpx
					recording = Resource(
						path=f'{summary.path[0:-3]}gpx',
						type=GPX_TYPE,
					)
					recording.data, recording.content = to_gpx( summary.raw.as_point_list() )

					for r in [ summary, recording ]:
						r.source, r.uid = source, uid

					dst_fs.makedirs( dirname( path ), recreate=True )
					for r in [ summary, recording ]:
						dst_fs.writebytes( r.path, contents=r.content )
						log.debug( f'wrote resource data to {r.path}' )

					# create activity and unload resources
					drive = self._drive_importer.load_as_activity( resource=summary, fs=dst_fs )
					drive.resources.append( recording )

					# update activity with gpx metadata
					gpx = recording.data
					drive.distance = gpx.length_2d()
					drive.duration = timedelta( seconds=gpx.get_duration() )
					drive.starttime, drive.endtime = gpx.get_time_bounds()
					drive.starttime_local, drive.endtime_local = drive.starttime.astimezone( tzlocal() ), drive.endtime.astimezone( tzlocal() )
					start_point, end_point = first( gpx.get_points_data() ), last( gpx.get_points_data() )
					drive.location_latitude_start, drive.location_longitude_start = start_point.point.latitude, start_point.point.longitude
					drive.location_latitude_end, drive.location_longitude_end = end_point.point.latitude, end_point.point.longitude
					
					# unload and append
					summary.unload()
					recording.unload()
					activities.append( drive )

					log.info( f'imported new Waze activity {drive.uid}' )

		# self.ctx.complete( 'done' )

		log.info( f'import created {len( activities )} new Waze activities' )

		return activities

	# noinspection PyMethodMayBeStatic
	def supports_remote_import( self ) -> bool:
		return False

# helper functions

def to_gpx( points: List[Point] ) -> Tuple[GPX, bytes]:
	trackpoints = [GPXTrackPoint( time=p.time, latitude=p.lat, longitude=p.lon ) for p in points]
	segment = GPXTrackSegment( points=trackpoints )
	track = GPXTrack()
	track.segments.append( segment )
	gpx = GPX()
	gpx.tracks.append( track )
	return gpx, bytes( gpx.to_xml(), 'UTF-8' )

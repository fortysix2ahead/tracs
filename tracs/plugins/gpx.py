
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Optional

from dateutil.tz import tzlocal
from dateutil.tz import UTC
from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX

from tracs.activity import Activity
from tracs.activity import Resource
from tracs.plugins import document
from tracs.plugins import importer
from tracs.plugins.handlers import ResourceHandler
from tracs.utils import seconds_to_time

log = getLogger( __name__ )

GPX_TYPE = 'application/xml+gpx'

@document( type=GPX_TYPE )
class GPXActivity( Activity ):

	def __raw_init__( self, raw: Any ) -> None:
		gpx: GPX = self.raw
		self.name = gpx.name
		self.time = gpx.get_time_bounds().start_time.astimezone( UTC )
		self.time_end = gpx.get_time_bounds().end_time.astimezone( UTC )
		self.localtime = self.time.astimezone( tzlocal() )
		self.localtime_end = self.time_end.astimezone( tzlocal() )
		self.distance = round( gpx.length_2d(), 1 )
		self.duration = seconds_to_time( gpx.get_duration() ) if gpx.get_duration() else None
		self.raw_id = int( self.time.strftime( '%y%m%d%H%M%S' ) )
		# self.uid = f'{self.classifier}:{self.raw_id}'

@importer( type=GPX_TYPE )
class GPXImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=GPX_TYPE, activity_cls=GPXActivity )

	def load_data( self, resource: Resource, **kwargs ) -> None:
		resource.raw = parse_gpx( resource.content )

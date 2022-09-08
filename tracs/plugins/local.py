
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Tuple

from . import Registry
from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
from ..service import Service

log = getLogger( __name__ )

# empty sample plugin

SERVICE_NAME = 'local'
DISPLAY_NAME = 'Local'

@document
class LocalActivity( Activity ):
	pass

@service
class Local( Service, Plugin ):

	def __init__( self, **kwargs  ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )

	def login( self ) -> bool:
		return True

	def _fetch( self, force: bool = False, **kwargs ) -> Iterable[Activity]:
		if path := kwargs.get( 'path' ):
			if path.is_file():
				activity = self.import_from_file( path )
				return [activity]
			elif path.is_dir():
				pass

		return []

	def import_from_file( self, path: Path ):
		if handler := Registry.document_handlers.get( path.suffix[1:] ):
			return self._prototype( handler().load( path ) )
		else:
			return None

	# noinspection PyMethodMayBeStatic
	def _prototype( self, activity ) -> Activity:
		activity.uid = f'{self.name}:{activity.raw_id}'
		activity.resources = [
			Resource( type='gpx', path=f'{activity.raw_id}.gpx', status=200, uid=activity.uid, raw_data=activity.raw_data ),
		]
		activity.raw_data = None
		return activity

	def download_resource( self, resource: Resource ) -> Tuple[Any, int]:
		return [], 200

	def setup( self ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

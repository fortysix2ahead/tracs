
from logging import getLogger
from pathlib import Path
from re import compile
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
		activities = []
		if path := kwargs.get( 'path' ):
			if path.is_file():
				activities = [ self.import_from_file( path ) ]
			elif path.is_dir():
				activities = [ self.import_from_file( f ) for f in path.iterdir() ]

		if kwargs.get( 'as_one', False ) and len( activities ) > 1:
			activity = Activity()
			for a in activities:
				activity.init_from( other=a )
				activity.resources.extend( a.resources )
			activities = [activity]

		if kwargs.get( 'move', False ):
			pass # todo: implement move

		return activities

	# noinspection PyMethodMayBeStatic
	def import_from_file( self, path: Path ) -> Any:
		importers = Registry.importers_for_suffix( path.suffix[1:] )
		imported_data = None
		for i in importers:
			try:
				imported_data = i.load( path=path )
				break
			except AttributeError:
				imported_data = None

		return imported_data

	# noinspection PyMethodMayBeStatic
	def _prototype( self, activity ) -> Activity:
		activity.uid = f'{self.name}:{activity.raw_id}'
		activity.resources[0].path = f'{activity.raw_id}.{activity.resources[0].type}'
		activity.resources[0].status = 200
		activity.resources[0].uid = activity.uid
		return activity

	def download_resource( self, resource: Resource ) -> Tuple[Any, int]:
		return [], 200

	def setup( self ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

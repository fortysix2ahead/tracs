
from logging import getLogger
from pathlib import Path
from re import compile
from typing import Any
from typing import Iterable
from typing import List
from typing import Optional
from typing import Optional
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

	def path_for( self, activity: Activity = None, resource: Resource = None, ext: Optional[str] = None ) -> Optional[Path]:
		"""
		Returns the path for an activity.

		:param activity: activity for which the path shall be calculated
		:param resource: resource
		:param ext: file extension
		:return: path for activity
		"""
		_id = str( activity.raw_id ) if activity else resource.raw_id()
		path = Path( self.base_path, _id[0:2], _id[2:4], _id[4:6], _id )
		if resource:
			path = Path( path, resource.path )
		elif ext:
			path = Path( path, f'{id}.{ext}' )
		return path

	def login( self ) -> bool:
		return True

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		activities = []
		if path := kwargs.get( 'path' ):
			if path.is_file():
				activities = [ self.import_from_file( path ) ]
			elif path.is_dir():
				activities = [ self.import_from_file( f ) for f in path.iterdir() ]

		# if kwargs.get( 'as_one', False ) and len( activities ) > 1:
		# 	activity = Activity()
		# 	for a in activities:
		# 		activity.init_from( other=a )
		# 		activity.resources.extend( a.resources )
		# 	activities = [activity]
		#
		# if kwargs.get( 'move', False ):
		# 	pass # todo: implement move

		resources = []
		for a in activities:
			for r in a.resources:
				r.uid = f'{self.name}:{a.time.strftime( "%y%m%d%H%M%S" )}'
				r.path = f'{r.raw_id()}.{r.path.rsplit( ".", 1 )[1]}'
			resources.extend( a.resources )
		return resources

	def postprocess( self, activity: Optional[Activity], resources: Optional[List[Resource]], **kwargs ) -> None:
		activity.uid = activity.resources[0].uid # todo: always correct?

	# noinspection PyMethodMayBeStatic
	def import_from_file( self, path: Path ) -> Any:
		importers = Registry.importers_for_suffix( path.suffix[1:] )
		try:
			imported_data = None
			for i in importers:
				imported_data = i.load( path=path )
				break
		except AttributeError:
			imported_data = None

		return imported_data

	def setup( self ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

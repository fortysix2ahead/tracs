
from logging import getLogger
from pathlib import Path
from shutil import move
from typing import Any
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import urlparse
from urllib.request import url2pathname

from . import Registry
from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
from ..config import ApplicationContext
from ..service import Service

log = getLogger( __name__ )

# plugin supporting local imports

SERVICE_NAME = 'local'
DISPLAY_NAME = 'Local'

@document
class LocalActivity( Activity ):
	pass

@service
class Local( Service, Plugin ):

	def __init__( self, **kwargs  ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )

	def path_for_id( self, local_id: Union[int, str], base_path: Optional[Path] ) -> Path:
		local_id = str( local_id )
		path = Path( local_id[0:2], local_id[2:4], local_id[4:6], local_id )
		return Path( base_path, path ) if base_path else path

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return None

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		return None

	def login( self ) -> bool:
		return True

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		resources = []

		if path := kwargs.get( 'path' ):
			if path.is_file():
				paths = [ path ]
			elif path.is_dir():
				paths = [ f for f in path.iterdir() ]
			else:
				paths = []

			for p in paths:
				activity = self.import_from_file( p )
				resource = activity.resources[0]
				resource.uid = f'{self.name}:{activity.time.strftime( "%y%m%d%H%M%S" )}'
				resource.path = f'{resource.local_id}.{resource.path.rsplit( ".", 1 )[1]}'
				resource.status = 200
				resources.append( resource )

		return resources

	def postprocess( self, activity: Optional[Activity], resources: Optional[List[Resource]], **kwargs ) -> None:
		# todo: is this always correct?
		activity.uid = activity.resources[0].uid

	def persist_resource_data( self, activity: Activity, force: bool, pretend: bool, **kwargs ) -> None:
		if kwargs.get( 'move', False ):
			for r in activity.resources:
				src_path = Path( urlparse( url2pathname( r.source ) ).path )
				dest_path = self.path_for( resource=r )
				dest_path.parent.mkdir( parents=True, exist_ok=True )
				move( src_path, dest_path )
		else:
			super().persist_resource_data( activity, force, pretend, **kwargs )

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

	def setup( self, ctx: ApplicationContext ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

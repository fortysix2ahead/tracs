
from logging import getLogger
from typing import Any
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
from ..config import ApplicationContext
from ..service import Service

log = getLogger( __name__ )

# empty sample plugin

SERVICE_NAME = 'empty'
DISPLAY_NAME = 'Empty Sample Service'

@document
class EmptyActivity( Activity ):
	pass

@service
class Empty( Service, Plugin ):

	def __init__( self, **kwargs  ):
		super().__init__( name=SERVICE_NAME, display_name=DISPLAY_NAME, **kwargs )

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return None

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		return None

	def login( self ) -> bool:
		return True

	def fetch( self, force: bool = False, **kwargs ) -> Iterable[Activity]:
		return []

	def download( self, activity: Optional[Activity] = None, summary: Optional[Resource] = None, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		return []

	def download_resource( self, resource: Resource, **kwargs ) -> Tuple[Any, int]:
		return [], 200

	def setup( self, ctx: ApplicationContext ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

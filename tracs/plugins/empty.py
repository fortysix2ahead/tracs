
from logging import getLogger
from typing import Any
from typing import Iterable
from typing import Tuple

from . import document
from . import service
from .plugin import Plugin
from ..activity import Activity
from ..activity import Resource
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

	def login( self ) -> bool:
		return True

	def _fetch( self, force: bool = False, **kwargs ) -> Iterable[Activity]:
		return []

	def download_resource( self, resource: Resource ) -> Tuple[Any, int]:
		return [], 200

	def setup( self ) -> None:
		pass

	# noinspection PyMethodMayBeStatic
	def setup_complete( self ) -> bool:
		return True

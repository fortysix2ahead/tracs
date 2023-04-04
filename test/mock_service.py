
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List
from typing import Optional
from typing import Union

from dateutil.tz import tzlocal

from tracs.activity import Activity
from tracs.config import ApplicationContext
from tracs.handlers import ResourceHandler
from tracs.plugins.gpx import GPX_TYPE
from tracs.registry import importer
from tracs.registry import resourcetype
from tracs.resources import Resource
from tracs.service import Service

MOCK_TYPE = 'application/mock+json'

@resourcetype( type=MOCK_TYPE, summary=True )
@dataclass
class MockActivity:

	uid: str = field( default=None )

	# noinspection PyMethodMayBeStatic
	def as_activity( self ) -> Activity:
		return Activity(
			uids = [self.uid],
			time = datetime.utcnow(),
			localtime = datetime.utcnow().astimezone( tzlocal() ),
		)

@importer( type=MOCK_TYPE )
class MockImporter( ResourceHandler ):

	def __init__( self ) -> None:
		super().__init__( resource_type=MOCK_TYPE, activity_cls=MockActivity )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		return MockActivity( uid=resource.uid )

class Mock( Service ):

	def __init__( self, **kwargs ):
		super().__init__( name='mock', display_name='Mock', **kwargs )

	def fetch( self, force: bool, pretend: bool, **kwargs ) -> List[Resource]:
		return [
			Resource( uid='mock:1001', path='1001.json', type=MOCK_TYPE, text='mock:1001' ),
			Resource( uid='mock:1002', path='1002.json', type=MOCK_TYPE, text='mock:1001' ),
			Resource( uid='mock:1003', path='1003.json', type=MOCK_TYPE, text='mock:1001' ),
		]

	def download( self, summary: Resource = None, force: bool = False, pretend: bool = False, **kwargs ) -> List[Resource]:
		return [Resource(
			uid=summary.uid,
			path=f'{summary.local_id}.gpx',
			type=GPX_TYPE
		)]

	def url_for_id( self, local_id: Union[int, str] ) -> str:
		pass

	def url_for_resource_type( self, local_id: Union[int, str], type: str ):
		pass

	def setup( self, ctx: ApplicationContext ) -> None:
		pass

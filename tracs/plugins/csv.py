
from csv import field_size_limit
from csv import reader as csv_reader
from typing import Optional
from typing import Type

from tracs.registry import importer
from tracs.handlers import ResourceHandler
from tracs.resources import Resource

CSV_TYPE = 'text/csv'

DEFAULT_FIELD_SIZE_LIMIT = 131072

@importer( type=CSV_TYPE )
class CSVHandler( ResourceHandler ):

	def __init__( self, resource_type: Optional[str] = None, activity_cls: Optional[Type] = None, **kwargs ) -> None:
		super().__init__( resource_type=resource_type or CSV_TYPE, activity_cls=activity_cls )

		self._field_size_limit = kwargs.get( 'field_size_limit', DEFAULT_FIELD_SIZE_LIMIT ) # keep this later use

	def load_data( self, resource: Resource, **kwargs ) -> None:
		resource.raw = [ r for r in csv_reader( self.as_str( resource.content ).splitlines() ) ]

	@property
	def field_size_limit( self ) -> int:
		return self._field_size_limit

	@field_size_limit.setter
	def field_size_limit( self, limit: int ) -> None:
		self._field_size_limit = limit
		field_size_limit( self._field_size_limit )

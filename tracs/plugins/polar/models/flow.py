from datetime import datetime
from re import match, compile
from typing import List, Optional

from attrs import define, field
from datetimerange import DateTimeRange

from tracs.activity_types import ActivityTypes
from tracs.plugins.polar.constants import ICON_TYPES
from tracs.resources import Resource

@define
class ResourcePartlist:

	index: int = field( default=0 )
	range: DateTimeRange = field( default=None )
	resources: List[Resource] = field( factory=list )

	def start( self ) -> datetime:
		return self.range.start_datetime

	def end( self ) -> datetime:
		return self.range.end_datetime

@define
class PolarFlowExercise:

	allDay: bool = field( default=False )
	backgroundColor: Optional[str] = field( default=None )
	borderColor: Optional[str] = field( default=None )
	calories: Optional[int] = field( default=None )
	className: Optional[str] = field( default=None )
	datetime: str = field( default=None ) # 2011-04-28T17:48:10.000Z
	distance: Optional[float] = field( default=None )
	duration: int = field( default=None )
	end: Optional[int] = field( default=None )
	eventType: str = field( default=None )
	hasTrainingTarget: Optional[bool] = field( default=False )
	iconUrl: Optional[str] = field( default=None )
	index: Optional[int] = field( default=None )
	isTest: Optional[bool] = field( default=False )
	listItemId: int = field( default=None )
	start: Optional[int] = field( default=None )
	textColor: Optional[str] = field( default=None )
	timestamp: int = field( default=None )
	title: str = field( default=None )
	type: str = field( default=None )
	url: str = field( default=None )

	@property
	def is_multipart( self ):
		return _is_multipart_id( self.iconUrl )

	@property
	def local_id( self ) -> int:
		if self.eventType == 'exercise' or self.eventType == 'fitnessData':
			return self.listItemId
		elif self.eventType == 'orthostaticTest':
			return int( match('.*id=(\d+).*', self.url )[1] )
		elif self.eventType == 'rrTest':
			return int( match('.*/rr/(\d+)', self.url )[1])
		return 0

	@property
	def uid( self ):
		return f'{SERVICE_NAME}:{self.local_id}'

	def get_type( self ) -> ActivityTypes:
		return ICON_TYPES.get( self.iconUrl.rsplit( '/', 1 )[1], ActivityTypes.unknown ) if self.iconUrl else ActivityTypes.unknown

@define
class PolarFitnessTest:

	allDay: bool = field( default=False )
	backgroundColor: str = field( default=None )
	borderColor: str = field( default=None )
	className: str = field( default=None )
	datetime: str = field( default=None ) # 2011-04-28T17:48:10.000Z
	eventType: str = field( default=None )
	index: int = field( default=None )
	listItemId: int = field( default=None )
	start: str = field( default=None )
	textColor: str = field( default=None )
	timestamp: int = field( default=None )
	title: str = field( default=None )
	type: str = field( default=None )
	url: str = field( default=None )

@define
class PolarOrthostaticTest:

	_RX_URL = compile( r'/progress/tests\?type=orthostatic_test&id=(\d+)' )

	datetime: str = field( default=None ) # 2011-04-28T17:48:10.000Z
	eventType: str = field( default=None )
	result: str = field( default=None )
	title: str = field( default=None )
	type: str = field( default=None )
	url: str = field( default=None )

	@property
	def local_id( self ) -> int:
		return int( self.__class__._RX_URL.fullmatch( self.url ).groups()[0] )

@define
class PolarRRRecording:

	_RX_URL = compile( r'/training/test/rr/(\d+)' )

	datetime: str = field( default=None ) # 2011-04-28T17:48:10.000Z
	eventType: str = field( default=None )
	result: str = field( default=None )
	title: str = field( default=None )
	type: str = field( default=None )
	url: str = field( default=None )

	@property
	def local_id( self ) -> int:
		return int( self.__class__._RX_URL.fullmatch( self.url ).groups()[0] )

@define
class PolarFlowExerciseCsv:

	pass

@define
class PolarFlowExerciseHrv:

	pass

@define
class PolarTrainingSession:

	pass

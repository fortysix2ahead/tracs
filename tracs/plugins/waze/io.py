from enum import Enum
from logging import getLogger
from typing import Any, Optional, Union

from dateutil.tz import gettz, UTC

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer
from tracs.plugins.csv import CSVHandler
from tracs.plugins.waze.constants import *
from tracs.plugins.waze.model import *
from tracs.resources import Resource
from tracs.utils import as_datetime

log = getLogger( __name__ )

@importer( type=WAZE_ACCOUNT_ACTIVITY_TYPE )
class WazeAccountActivityImporter( CSVHandler ):

	TYPE = WAZE_ACCOUNT_ACTIVITY_TYPE

	class Mode( Enum ):
		NONE = 'NONE'
		DRIVE_SUMMARY = '\ufeffdrive summary'
		FAVOURITES = 'favorites'
		LOCATION_DETAILS = 'location details'
		LOCATION_DETAILS_2 = 'location details (date, time, coordinates)'
		LOGIN_DETAILS = 'login details'
		USAGE_DATA_SNAPSHOT = 'snapshot of your waze usage'
		EDIT_HISTORY = 'edit history'
		PHOTOS_ADDED = 'photos added to the map'
		USER_REPORTS = 'user reports'
		USER_FEEDBACK = 'user feedback'
		SEARCH_HISTORY = 'search history'
		CARPOOL_PREFERENCES = 'carpool preferences'

		@classmethod
		def mode_by_value( cls, line: Union[str, List[str]] ):
			# print( f'mode by value for: {line}' )

			# special treatment ...
			if line == [ 'Location details (date', ' time', ' coordinates)' ]:
				line = [ 'Location details (date, time, coordinates)' ]

			if len( line ) != 1:
				return cls.NONE

			return next( iter( [m for m in cls if m.value == line[0].lower()] ), cls.NONE )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		account_activity = AccountActivity()
		while raw:
			line = raw.pop( 0 )
			mode = WazeAccountActivityImporter.Mode.mode_by_value( line )

			if mode == WazeAccountActivityImporter.Mode.DRIVE_SUMMARY:
				while line:
					if (line := raw.pop( 0 )) and line != ['Date', 'Destination', 'Source']:
						account_activity.drive_summaries.append( DriveSummary( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.FAVOURITES:
				while line:
					if (line := raw.pop( 0 )) and line != ['Place', 'Name', 'Type']:
						account_activity.favourites.append( Favourite( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.LOCATION_DETAILS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Date', 'Coordinates']:
						account_activity.location_details.append( LocationDetail( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.LOCATION_DETAILS_2:
				while line:
					if line := raw.pop( 0 ):
						account_activity.location_details.append( LocationDetail( coordinates=line[0] ) )

			elif mode == WazeAccountActivityImporter.Mode.LOGIN_DETAILS:
				while line:
					if (line := raw.pop( 0 )) and line[0] != 'Login Time' and line[1] != 'Logout Time':
						account_activity.login_details.append( LoginDetail( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USAGE_DATA_SNAPSHOT:
				header = raw.pop( 0 )
				data = raw.pop( 0 )
				for h, d in zip( header, data ):
					setattr( account_activity.usage_data, _snake( h ), d )

			elif mode == WazeAccountActivityImporter.Mode.EDIT_HISTORY:
				while line:
					if line := raw.pop( 0 ):
						account_activity.edit_history.append( EditHistoryEntry( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USER_REPORTS:
				while line:
					if line := raw.pop( 0 ):
						account_activity.user_reports.append( UserReport( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.USER_FEEDBACK:
				while line:
					if line := raw.pop( 0 ):
						account_activity.user_feedback.append( UserFeedback( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.PHOTOS_ADDED:
				while line:
					if (line := raw.pop( 0 )) and line != ['Name', 'Image']:
						account_activity.photos_added.append( Photo( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.SEARCH_HISTORY:
				while line:
					if line := raw.pop( 0 ):
						account_activity.search_history.append( SearchHistoryEntry( *line ) )

			elif mode == WazeAccountActivityImporter.Mode.CARPOOL_PREFERENCES:
				header = raw.pop( 0 )
				data = raw.pop( 0 )
				for h, d in zip( header, data ):
					setattr( account_activity.carpool_preferences, _snake( h ), d )

			else:
				if line:
					log.error( f'unsupported CSV section detected: "{line}"' )

		return account_activity

@importer( type=WAZE_ACCOUNT_INFO_TYPE )
class WazeAccountInfoImporter( CSVHandler ):

	TYPE = WAZE_ACCOUNT_INFO_TYPE

	class Mode( Enum ):
		NONE = 'NONE'
		GENERAL_INFO = '\ufeffgeneral info'
		CONNECTED_ACCOUNTS = 'connected accounts'
		USER_REPORTS = 'user reports'
		USER_FEEDBACK = 'user feedback'
		USER_COUNTERS = 'user counters'

		@classmethod
		def mode_by_value( cls, line: str ):
			if len( line ) != 1:
				return cls.NONE
			return next( iter( [m for m in cls if m.value == line[0].lower()] ), cls.NONE )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		account_info = AccountInfo()
		while raw:
			line = raw.pop( 0 )
			mode = WazeAccountInfoImporter.Mode.mode_by_value( line )

			if mode == WazeAccountInfoImporter.Mode.GENERAL_INFO:
				while line:
					if line := raw.pop( 0 ):
						setattr( account_info, _snake( line[0] ), line[1] )

			elif mode == WazeAccountInfoImporter.Mode.CONNECTED_ACCOUNTS:
				while line:
					if line := raw.pop( 0 ):
						account_info.connected_accounts.append( line[0] )

			elif mode == WazeAccountInfoImporter.Mode.USER_REPORTS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Event Date', 'Type', 'Pos X', 'Pos Y', 'Subtype']:
						account_info.user_reports.append( UserReport( *line ) )

			elif mode == WazeAccountInfoImporter.Mode.USER_FEEDBACK:
				while line:
					if (line := raw.pop( 0 )) and line != ['Event Date','Type','Alert Type']:
						account_info.user_feedback.append( UserFeedback( *line ) )

			elif mode == WazeAccountInfoImporter.Mode.USER_COUNTERS:
				while line:
					if (line := raw.pop( 0 )) and line != ['Count','Name']:
						setattr( account_info.user_counters, line[1], line[0] )

		return account_info

@importer( type=WAZE_TYPE )
class WazeImporter( ResourceHandler ):

	TYPE: str = WAZE_TYPE
	ACTIVITY_CLS = WazeActivity

	def load_raw( self, content: Union[bytes,str], **kwargs ) -> Any:
		return LocationDetail( coordinates=content.decode( 'UTF-8' ) )

	def load_data( self, raw: Any, **kwargs ) -> Any:
		return WazeActivity( raw.as_point_list() )

	def as_activity( self, resource: Resource ) -> Optional[Activity]:
		wa: WazeActivity = resource.data
		return Activity(
			starttime=as_datetime( wa.points[0].time, tz=UTC ),
			starttime_local=as_datetime( wa.points[0].time, tz=gettz() ),
			type=ActivityTypes.drive,
			uid=f'{SERVICE_NAME}:{wa.points[0].time_as_int()}'
		)


# helper

def _snake( s: str ) -> str:
	return s.lower().replace( ' ', '_' )

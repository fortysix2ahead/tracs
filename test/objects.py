from datetime import datetime, timedelta

from dateutil.tz import UTC

from activity import Activity, ActivityPart
from activity_types import ActivityTypes
from core import Metadata
from plugins.gpx import GPX_TYPE
from resources import Resource, Resources
from uid import UID

# collection of test objects

COMPLETE_ACTIVITY = Activity(
	id=1,
	uid='polar:101',
	starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
	duration=timedelta( hours=2 ),
	type=ActivityTypes.walk,
	location_country='de',
	metadata=Metadata(
		created = datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified = datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite = True,
		members = [ UID( 'polar:101' ), UID( 'strava:101' ) ],
	),
	parts=[ActivityPart( uids=['polar:222', 'polar:333'], gap=timedelta( minutes=20 ) )],
	resources=Resources(
		Resource( name = 'recording.gpx', type=GPX_TYPE, path='polar/1/2/3/1234/1234.gpx', source='https://polar.com/1234/1234.gpx' )
	)
)

COMPLETE_ACTIVITY_DICT = {
	'id': 1,
	'uid': 'polar:101',
	'type': 'walk',
	'location_country': 'de',
	'starttime': '2024-01-03T10:00:00+00:00',
	'duration': '02:00:00',
	'metadata': {
		'created': '2024-01-04T10:00:00+00:00',
		'modified': '2024-01-04T11:00:00+00:00',
		'favourite': True,
		'members': ['polar:101', 'strava:101']
	},
	'parts': [
		{'gap': '00:20:00', 'uids': ['polar:222', 'polar:333']}
	],
	'resources': [
		{ 'name': 'recording.gpx', 'path': 'polar/1/2/3/1234/1234.gpx', 'source': 'https://polar.com/1234/1234.gpx', 'type': 'application/gpx+xml' }
	]
}

from datetime import datetime, timedelta
from typing import Optional

from dateutil.tz import tzlocal, tzoffset, UTC

from tracs.activity import Activity, ActivityPart, Activities
from tracs.activity_types import ActivityTypes
from tracs.core import Metadata
from tracs.plugins.gpx import GPX_TYPE
from tracs.resources import Resource, Resources
from tracs.uid import UID

# collection of test objects

# UID

UID_OBJ = UID( classifier='polar', local_id=101, path='recording.gpx', part=1 )

UID_DUMP = 'polar:101/recording.gpx#1'

# metadata

METADATA_OBJ = Metadata(
	created=datetime( 2024, 10, 10, 10, 10, 10, tzinfo=UTC ),
	modified=datetime( 2024, 11, 11, 11, 11, 11, tzinfo=UTC ),
	favourite=True,
	members=[
		UID.of( 'polar:101' ),
		UID.of( 'strava:101' )
	],
)

METADATA_OBJ_DUMP = \
'''{
  "created": "2024-10-10T10:10:10+00:00",
  "favourite": true,
  "members": [
    "polar:101",
    "strava:101"
  ],
  "modified": "2024-11-11T11:11:11+00:00"
}
'''

# resources

RESOURCE_OBJ = Resource(
	name='recording.gpx',
	path='polar/1/2/3/1234/1234.gpx',
	source='https://polar.com/1234/1234.gpx',
	type=GPX_TYPE,
	uid=UID.of( 'polar:1234' ),
)

RESOURCE_OBJ_DUMP = \
'''{
  "name": "recording.gpx",
  "path": "polar/1/2/3/1234/1234.gpx",
  "source": "https://polar.com/1234/1234.gpx",
  "type": "application/gpx+xml",
  "uid": "polar:1234"
}
'''

RESOURCES_OBJ = Resources(
	Resource(
		name='recording_1.gpx',
		path='polar/1/2/3/1234/1234_1.gpx',
		source='https://polar.com/1234/1234_1.gpx',
		type=GPX_TYPE,
		uid=UID.of( 'polar:1234' ),
	),
	Resource(
		name='recording_2.gpx',
		path='polar/1/2/3/1234/1234_2.gpx',
		source='https://polar.com/1234/1234_2.gpx',
		type=GPX_TYPE,
		uid=UID.of( 'polar:1235' ),
	)
)

RESOURCES_OBJ_DUMP  = \
'''[
  {
    "name": "recording_1.gpx",
    "path": "polar/1/2/3/1234/1234_1.gpx",
    "source": "https://polar.com/1234/1234_1.gpx",
    "type": "application/gpx+xml",
    "uid": "polar:1234"
  },
  {
    "name": "recording_2.gpx",
    "path": "polar/1/2/3/1234/1234_2.gpx",
    "source": "https://polar.com/1234/1234_2.gpx",
    "type": "application/gpx+xml",
    "uid": "polar:1235"
  }
]
'''

# activity part

ACTIVITY_PART_OBJ = ActivityPart(
	gap=timedelta( minutes=20 ),
	uid=UID.of( 'polar:1234/recording.1.gpx' )
)

ACTIVITY_PART_OBJ_DUMP = \
'''{
  "gap": "00:20:00",
  "uid": "polar:1234/recording.1.gpx"
}
'''

# activity

ACTIVITY_OBJ = Activity(
	id=1,
	uid=UID.of( 'polar:1234' ),
	starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
	duration=timedelta( hours=2 ),
	type=ActivityTypes.walk,
	location_country='de',
	metadata=Metadata(
		created=datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified=datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite=True,
		members=[ UID.of( 'polar:101' ), UID.of( 'strava:101' ) ],
	),
#	parts=[
#		ActivityPart( uid=UID.of( 'polar:222#1' ), gap=timedelta( minutes=20 ) ),
#		ActivityPart( uid=UID.of( 'polar:222#2' ), gap=timedelta( minutes=20 ) )
#	],
	resources=Resources(
		Resource(
			name='recording.gpx',
			type=GPX_TYPE,
			path='polar/1/2/3/1234/1234.gpx',
			source='https://polar.com/1234/1234.gpx',
			uid='polar:1234',
		)
	)
)

ACTIVITY_OBJ_DUMP = \
'''{
  "duration": "02:00:00",
  "id": 1,
  "location_country": "de",
  "metadata": {
    "created": "2024-01-04T10:00:00+00:00",
    "favourite": true,
    "members": [
      "polar:101",
      "strava:101"
    ],
    "modified": "2024-01-04T11:00:00+00:00"
  },
  "parts": [
    {
      "gap": "00:20:00",
      "uid": "polar:222#1"
    },
    {
      "gap": "00:20:00",
      "uid": "polar:222#2"
    }
  ],
  "resources": [
    {
      "name": "recording.gpx",
      "path": "polar/1/2/3/1234/1234.gpx",
      "source": "https://polar.com/1234/1234.gpx",
      "type": "application/gpx+xml",
      "uid": "polar:1234"
    }
  ],
  "starttime": "2024-01-03T10:00:00+00:00",
  "type": "Walking",
  "uid": "polar:1234"
}
'''

ACTIVITIES_OBJ = Activities(
	Activity(
		id=2,
		uid=UID.of( 'polar:2234' ),
		starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
		duration=timedelta( hours=2 ),
		type=ActivityTypes.walk,
		location_country='de',
		metadata=Metadata(
			created=datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
			modified=datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
			favourite=True,
			members=[UID.of( 'polar:101' ), UID.of( 'strava:101' )],
		),
#		parts=[
#			ActivityPart( uid=UID.of( 'polar:222#1' ), gap=timedelta( minutes=20 ) ),
#			ActivityPart( uid=UID.of( 'polar:222#2' ), gap=timedelta( minutes=20 ) )
#		],
		resources=Resources(
			Resource(
				name='recording.gpx',
				type=GPX_TYPE,
				path='polar/1/2/3/1234/1234.gpx',
				source='https://polar.com/1234/1234.gpx',
				uid='polar:1234',
			)
		)
	)
)

ACTIVITIES_OBJ_DUMP = \
'''[
  {
    "duration": "02:00:00",
    "id": 2,
    "location_country": "de",
    "metadata": {
      "created": "2024-01-04T10:00:00+00:00",
      "favourite": true,
      "members": [
        "polar:101",
        "strava:101"
      ],
      "modified": "2024-01-04T11:00:00+00:00"
    },
    "parts": [
      {
        "gap": "00:20:00",
        "uid": "polar:222#1"
      },
      {
        "gap": "00:20:00",
        "uid": "polar:222#2"
      }
    ],
    "resources": [
      {
        "name": "recording.gpx",
        "path": "polar/1/2/3/1234/1234.gpx",
        "source": "https://polar.com/1234/1234.gpx",
        "type": "application/gpx+xml",
        "uid": "polar:1234"
      }
    ],
    "starttime": "2024-01-03T10:00:00+00:00",
    "type": "Walking",
    "uid": "polar:2234"
  }
]
'''

COMPLETE_ACTIVITY = Activity(
	id=1,
	uid='polar:101',
	starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
	duration=timedelta( hours=2 ),
	type=ActivityTypes.walk,
	location_country='de',
	metadata=Metadata(
		created=datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified=datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite=True,
		members=[UID( 'polar:101' ), UID( 'strava:101' )],
	),
#	parts=[
#		ActivityPart( uid=UID.from_str( 'polar:222#1' ), gap=timedelta( minutes=20 ) ),
#		ActivityPart( uid=UID.from_str( 'polar:222#2' ), gap=timedelta( minutes=20 ) )
#	],
	resources=Resources(
		Resource(
			name='recording.gpx',
			type=GPX_TYPE,
			path='polar/1/2/3/1234/1234.gpx',
			source='https://polar.com/1234/1234.gpx',
			uid='polar:1234',
		)
	)
)

COMPLETE_ACTIVITY_WITH_RESOURCE_DATA = Activity(
	id=1,
	uid=UID.from_str( 'polar:101' ),
	starttime=datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC ),
	duration=timedelta( hours=2 ),
	type=ActivityTypes.walk,
	location_country='de',
	metadata=Metadata(
		created=datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		modified=datetime( 2024, 1, 4, 11, 0, 0, tzinfo=UTC ),
		favourite=True,
		members=[UID( 'polar:101' ), UID( 'strava:101' )],
	),
#	parts=[
#		ActivityPart( uid=UID.from_str( 'polar:222#1' ), gap=timedelta( minutes=20 ) ),
#		ActivityPart( uid=UID.from_str( 'polar:222#2' ), gap=timedelta( minutes=20 ) )
#	],
	resources=Resources(
		Resource(
			name='recording.gpx',
			type=GPX_TYPE,
			path='polar/1/2/3/1234/1234.gpx',
			source='https://polar.com/1234/1234.gpx',
			uid=UID.from_str( 'polar:1234' ),
			content=b'<xml></xml>',
			text='<xml></xml>',
			raw={ 'xml': 'some data' },
			data={ 'xml': 'some data' },
		)
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
		{ 'gap': '00:20:00', 'uid': 'polar:222#1' },
		{ 'gap': '00:20:00', 'uid': 'polar:222#2' }
	],
	'resources': [
		{
			'name': 'recording.gpx',
			'path': 'polar/1/2/3/1234/1234.gpx',
			'source': 'https://polar.com/1234/1234.gpx',
			'type': 'application/gpx+xml',
			# 'uid': UID( 'polar:1234' ),
			'uid': 'polar:1234'
		}
	]
}

DEFAULT_ONE = Activity(
	id=1,
	name='Unknown Location',
	type=ActivityTypes.xcski,
	starttime=datetime( 2012, 1, 7, 10, 40, 56, tzinfo=UTC ),
	#starttime_local=datetime( 2012, 1, 7, 11, 40, 56, tzinfo=tzlocal() ),
	starttime_local=datetime( 2012, 1, 7, 11, 40, 56, tzinfo=tzoffset(None, 3600) ),
	location_place='Forest',
	uid='group:1',
	metadata=Metadata(
		members=UID.from_strs( ['polar:1234567890', 'strava:12345678', 'waze:20210101010101'] )
	)
)

def activity( id: int = 0, uid: Optional[str] = None, name: Optional[str] = None ):
	return Activity(
		id=id,
		uid=UID.of( uid or f'activity:{id}' ),
		name=name or f'Activity {id}',
	)

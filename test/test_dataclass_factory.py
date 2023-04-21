from dataclass_factory import Factory, Schema as DataclassFactorySchema
from datetime import datetime

from dateutil.tz import tzlocal
from rich.pretty import pprint as pp

from tracs.activity import Activity, ActivityPart
from tracs.activity_types import ActivityTypes
from tracs.db import Schema
from tracs.resources import Resource

def activity_pre_serialize( a: Activity ) -> Activity:
	a.uids.append( 'waze:101' )
	return a

ACTIVITY_SCHEMA = DataclassFactorySchema(
	exclude=['id'],
	omit_default=True,
	pre_serialize=activity_pre_serialize,
	skip_internal=True,
	unknown='unknown'
)

F = Factory(
	debug_path=True,
	schemas={
		Activity: ACTIVITY_SCHEMA,
		ActivityPart: DataclassFactorySchema( omit_default=True, skip_internal=True, unknown='unknown' ),
		ActivityTypes: DataclassFactorySchema( parser=ActivityTypes.from_str, serializer=ActivityTypes.to_str ),
		Resource: DataclassFactorySchema( omit_default=True, skip_internal=True, unknown='unknown',
		                                  exclude=['content', 'data', 'id', 'raw', 'resources', 'status', 'summary', 'text'] ),
		Schema: DataclassFactorySchema( skip_internal=True ),
	}
)

def test_serialize():
	a = Activity(
		time=datetime.utcnow(),
		localtime=datetime.now( tzlocal() ),
		uids=['polar:101', 'strava:101']
	)
	pp( F.dump( a ) )

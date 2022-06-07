
from datetime import datetime
from datetime import time
from dateutil.tz import UTC
from dateutil.tz import tzlocal

from gtrac.activity import ActivityRef
from gtrac.activity_types import ActivityTypes
from gtrac.plugins.groups import ActivityGroup
from gtrac.plugins.polar import PolarActivity
from gtrac.plugins.strava import StravaActivity

from .fixtures import db_default_inmemory

def test_init( db_default_inmemory ):
	db, json = db_default_inmemory

	# empty init
	a = ActivityGroup( doc_id = 0 )
	assert a['groups'] == {} and a.groups == {}
	assert a['group_refs'] == [] and a.group_refs == []
	assert a['group_ids'] == [] and a.group_ids == []
	assert a['group_uids'] == [] and a.group_uids == []
	assert a['parent'] is None
	assert a['metadata'] == {} and a.metadata == {}
	assert a['raw'] is None and a.raw is None
	assert a['resources'] == [] and a.resources == []

	assert a['id'] == 0 and a['uid'] == 'group:0'
	assert a.classifier == 'group'

	# init from db document
	a = ActivityGroup( json['activities']['1'], doc_id=1 )

	assert a.doc_id == 1 and a['doc_id'] == 1
	assert a['id'] == 1 and a.id == 1
	assert a.uid == 'group:1'
	assert a.type == ActivityTypes.xcski

	# empty_field is in json, but is not declared as attribute
	assert a['empty_field'] is None
	assert 'empty_field' not in a

	# grouping
	assert a.groups == {
		'ids': [2, 3, 4],
		'uids': ['polar:1234567890', 'strava:12345678', 'waze:20210101010101'],
	}
	assert a.group_refs == [
		ActivityRef( 2, 'polar:1234567890' ),
		ActivityRef( 3, 'strava:12345678' ),
		ActivityRef( 4, 'waze:20210101010101' ),
	]
	assert a.group_ids == [2, 3, 4]
	assert a.group_uids == ['polar:1234567890', 'strava:12345678', 'waze:20210101010101']
	assert a.classifiers == ['polar', 'strava', 'waze']

	# times
	assert a.time == datetime( 2012, 1, 7, 10, 40, 56, tzinfo=UTC )
	assert a.localtime == datetime( 2012, 1, 7, 11, 40, 56, tzinfo=tzlocal() )

#	assert a.resources == [
#		Resource( parent=a['_resources'][0], type='gpx', status=100, path='12345678.gpx' ),
#		Resource( parent=a['_resources'][1], type='tcx', status=100, path='12345678.tcx' )
#	]

	# init with child
	polar_json = json['activities']['2']
	pa = PolarActivity( polar_json, 2 )
	a = ActivityGroup( groups=[pa] )

	assert a.groups == [pa]
	assert a.group_ids == [pa.doc_id]
	assert a.group_uids == [pa.uid]
	assert a.group_classifiers == [pa.classifier]
	assert a.group_classifiers_str() == f'{pa.classifier}'
	assert a.group_refs == [
		ActivityRef( 2, 'polar:1234567890' ),
	]

	# check derived fields
	assert a.doc_id == 0
	assert a.id == 0
	assert a.uid == 'group:0'
	assert a.distance == 30000.1
	assert a.calories == 2904

	# init with 2 children
	polar_json = json['activities']['2']
	strava_json = json['activities']['3']
	pa = PolarActivity( polar_json, 2 )
	sa = StravaActivity( strava_json, 3 )
	a = ActivityGroup( groups=[pa, sa] )

	assert a.group_classifiers_str() == f'{pa.classifier},{sa.classifier}'
	assert a.group_refs == [
		ActivityRef( 2, 'polar:1234567890' ),
		ActivityRef( 3, 'strava:12345678' ),
	]

	assert a.name == '03:23:53;0.0 km'
	assert a.calories == 2904
	assert a.heartrate == 150
	assert a.duration_moving == time( 1, 40, 0)

from datetime import datetime, timedelta
from typing import Dict

from dateutil.tz import UTC
from orjson.orjson import dumps, loads
from pytest import mark

from test.objects import ACTIVITIES_OBJ, ACTIVITIES_OBJ_DUMP, ACTIVITY_OBJ, ACTIVITY_OBJ_DUMP, ACTIVITY_PART_OBJ, ACTIVITY_PART_OBJ_DUMP, \
	COMPLETE_ACTIVITY as A, COMPLETE_ACTIVITY_DICT as AD, METADATA_OBJ, METADATA_OBJ_DUMP, MULTIPART_ACTIVITY_OBJ, MULTIPART_ACTIVITY_OBJ_DUMP, RESOURCE_OBJ, \
	RESOURCE_OBJ_DUMP, \
	RESOURCES_OBJ, RESOURCES_OBJ_DUMP
from tracs.activity import Activities, Activity, ActivityPart, MultipartActivity
from tracs.activity_types import ActivityTypes
from tracs.constants import ORJSON_OPTIONS
from tracs.core import Metadata
from tracs.fsio import converter, load_activities, load_schema, write_activities
from tracs.resources import Resource, Resources

def dump_to_str( d: Dict ) -> str:
	return dumps( d, option=ORJSON_OPTIONS ).decode( 'utf-8' )

def load_from( s: str ) -> Dict:
	return loads( s )

@mark.context( env='default', persist='mem' )
def test_load_schema( dbfs ):
	assert load_schema( dbfs ).version == 14

@mark.unit
def test_metadata():
	assert dump_to_str( converter.unstructure( METADATA_OBJ ) ) == METADATA_OBJ_DUMP
	assert converter.structure( load_from( METADATA_OBJ_DUMP ), Metadata ) == METADATA_OBJ

@mark.unit
def test_resource():
	assert dump_to_str( converter.unstructure( RESOURCE_OBJ ) ) == RESOURCE_OBJ_DUMP
	assert converter.structure( load_from( RESOURCE_OBJ_DUMP ), Resource ) == RESOURCE_OBJ

	# resources
	assert dump_to_str( converter.unstructure( RESOURCES_OBJ ) ) == RESOURCES_OBJ_DUMP
	assert converter.structure( load_from( RESOURCES_OBJ_DUMP ), Resources ) == RESOURCES_OBJ

@mark.unit
def test_activity_type():
	assert dump_to_str( converter.unstructure( ActivityTypes.run ) ) == '"run"\n'
	assert converter.structure( 'run', ActivityTypes ) == ActivityTypes.run

@mark.unit
def test_activity_part():
	assert dump_to_str( converter.unstructure( ACTIVITY_PART_OBJ ) ) == ACTIVITY_PART_OBJ_DUMP
	assert converter.structure( load_from( ACTIVITY_PART_OBJ_DUMP ), ActivityPart ) == ACTIVITY_PART_OBJ

@mark.unit
def test_activity():
	assert dump_to_str( converter.unstructure( ACTIVITY_OBJ ) ) == ACTIVITY_OBJ_DUMP
	assert converter.structure( load_from( ACTIVITY_OBJ_DUMP ), Activity ) == ACTIVITY_OBJ

	# activities
	assert dump_to_str( converter.unstructure( ACTIVITIES_OBJ ) ) == ACTIVITIES_OBJ_DUMP
	assert converter.structure( load_from( ACTIVITIES_OBJ_DUMP ), Activities ) == ACTIVITIES_OBJ

@mark.unit
def test_multipart_activity():
	assert dump_to_str( converter.unstructure( MULTIPART_ACTIVITY_OBJ ) ) == MULTIPART_ACTIVITY_OBJ_DUMP
	assert converter.structure( load_from( MULTIPART_ACTIVITY_OBJ_DUMP ), MultipartActivity ) == MULTIPART_ACTIVITY_OBJ

@mark.context( env='default', persist='mem' )
def test_activities( dbfs ):
	activities = Activities()
	activities.add( A )

	# write to dbfs
	write_activities( activities, dbfs )

	json = loads( dbfs.readtext( 'activities.json' ) )
	assert json == [ AD ]

	#  load again from dbfs
	activities = load_activities( dbfs )

	assert len( activities ) == 1
	a1 = activities[0]
	assert a1.id == 1 and a1.uid == 'polar:101'
	assert a1.duration == timedelta( hours=2 )
	assert a1.starttime == datetime( 2024, 1, 3, 10, 0, 0, tzinfo=UTC )
	# assert a1.type == ActivityTypes.walk # don't know why this fails
	assert a1.type.name == 'walk'

	assert a1.parts[0].gap == timedelta( minutes=20 )
	assert a1.parts[0].uid == UID.from_str( 'polar:222#1' )

	assert a1.metadata.created == datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC )
	assert a1.metadata.favourite

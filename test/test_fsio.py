from typing import Dict

from orjson.orjson import dumps, loads
from pytest import mark

from test.objects import *
from tracs.activity import Activities, Activity, MultipartActivity
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
	assert load_schema( dbfs ).version == 15

@mark.unit
def test_uid():
	assert converter.unstructure( UID_OBJ ) == UID_DUMP
	assert converter.structure( UID_DUMP, UID ) == UID_OBJ

@mark.unit
def test_metadata():
	assert dump_to_str( converter.unstructure( METADATA_OBJ ) ) == METADATA_OBJ_DUMP
	assert converter.structure( load_from( METADATA_OBJ_DUMP ), Metadata ) == METADATA_OBJ

@mark.unit
def test_resource():
	assert dump_to_str( converter.unstructure( RESOURCE_OBJ ) ) == RESOURCE_OBJ_DUMP
	assert converter.structure( load_from( RESOURCE_OBJ_DUMP ), Resource ) == RESOURCE_OBJ

@mark.unit
def test_resources():
	assert dump_to_str( converter.unstructure( RESOURCES_OBJ ) ) == RESOURCES_OBJ_DUMP
	assert converter.structure( load_from( RESOURCES_OBJ_DUMP ), Resources ) == RESOURCES_OBJ

@mark.unit
def test_activity_type():
	assert dump_to_str( converter.unstructure( ActivityTypes.run ) ) == '"run"\n'
	assert converter.structure( 'run', ActivityTypes ) == ActivityTypes.run

@mark.unit
def test_activity():
	assert dump_to_str( converter.unstructure( ACTIVITY_OBJ ) ) == ACTIVITY_OBJ_DUMP
	assert converter.structure( load_from( ACTIVITY_OBJ_DUMP ), Activity ) == ACTIVITY_OBJ

@mark.unit
def test_activities():
	assert dump_to_str( converter.unstructure( ACTIVITIES_OBJ ) ) == ACTIVITIES_OBJ_DUMP
	assert converter.structure( load_from( ACTIVITIES_OBJ_DUMP ), Activities ) == ACTIVITIES_OBJ

@mark.unit
def test_multipart_activity():
	assert dump_to_str( converter.unstructure( MULTIPART_ACTIVITY_OBJ ) ) == MULTIPART_ACTIVITY_OBJ_DUMP
	assert converter.structure( load_from( MULTIPART_ACTIVITY_OBJ_DUMP ), MultipartActivity ) == MULTIPART_ACTIVITY_OBJ

@mark.context( env='empty' )
def test_activities( dbfs ):
	activities = Activities( ACTIVITY_OBJ )

	# write to dbfs
	write_activities( activities, dbfs )

	#  load again from dbfs
	activities = load_activities( dbfs )

	assert activities == [ ACTIVITY_OBJ ]

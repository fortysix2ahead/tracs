
from datetime import datetime
from datetime import time
from datetime import timezone
from dateutil.tz import tzlocal

from tracs.activity import ActivityRef
from tracs.plugins.polar import PolarActivity

from .fixtures import db_default_inmemory

from tracs.activity_types import ActivityTypes

def test_init_from_db( db_default_inmemory ):
	db, json = db_default_inmemory

	pa = PolarActivity( json['activities']['2'], 2 )
	assert pa.groups == { "parent": 1 }
	assert pa.parent_id == 1
	assert pa.parent_uid == 'group:1'
	assert pa.parent_ref == ActivityRef( 1, 'group:1' )

	pa = PolarActivity( json['activities']['11'], 11 )

	assert pa.raw_id == 1001
	assert pa.name == '00:25:34;0.0 km'
	assert pa.type == ActivityTypes.run
	assert pa.time == datetime( 2011, 4, 28, 15, 48, 10, tzinfo=timezone.utc )
	assert pa.localtime == datetime( 2011, 4, 28, 17, 48, 10, tzinfo=tzlocal() )
	assert pa.distance == 12000.3
	assert pa.duration == time( 0, 25, 35 )
	assert pa.calories == 456

def test_fitnessdata( db_default_inmemory ):
	db, json = db_default_inmemory
	json = json['activities']['12']
	pa = PolarActivity( json, 12 )

	assert pa.id == 12
	assert pa.raw_id == 2002

def test_orthostatic( db_default_inmemory ):
	db, json = db_default_inmemory
	json = json['activities']['13']
	pa = PolarActivity( json, 13 )

	assert pa['id'] == 13
	assert pa.id == 13
	assert pa.raw_id == 3003

def test_rrrecording( db_default_inmemory ):
	db, json = db_default_inmemory
	json = json['activities']['14']
	pa = PolarActivity( json, 14 )

	# test id
	assert pa['id'] == 14
	assert pa.id == 14
	assert pa.raw_id == 4004

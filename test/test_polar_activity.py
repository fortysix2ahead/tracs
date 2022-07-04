
from datetime import datetime
from datetime import time
from datetime import timezone
from pathlib import Path

from dateutil.tz import tzlocal

from pytest import mark

from tracs.plugins.handlers import JSONHandler
from tracs.plugins.polar import PolarActivity
from tracs.activity_types import ActivityTypes

from .helpers import get_file_path

@mark.db( template='polar' )
def test_init_from_db( json ):
	pa = PolarActivity( json['_default']['2'], 2 )
	assert pa.parent_id == 1
	assert pa.parent_uid == 'group:1'
	# assert pa.parent_ref == ActivityRef( 1, 'group:1' )

	pa = PolarActivity( json['_default']['11'], 11 )

	assert pa.raw_id == 1001
	assert pa.name == '00:25:34;0.0 km'
	assert pa.type == ActivityTypes.run
	assert pa.time == datetime( 2011, 4, 28, 15, 48, 10, tzinfo=timezone.utc )
	assert pa.localtime == datetime( 2011, 4, 28, 17, 48, 10, tzinfo=tzlocal() )
	assert pa.distance == 12000.3
	assert pa.duration == time( 0, 25, 35 )
	assert pa.calories == 456

@mark.db( template='polar' )
def test_fitnessdata( json ):
	json = json['_default']['12']
	pa = PolarActivity( json, 12 )

	assert pa.id == 12
	assert pa.raw_id == 2002

@mark.db( template='polar' )
def test_orthostatic( json ):
	json = json['_default']['13']
	pa = PolarActivity( json, 13 )

	assert pa['id'] == 13
	assert pa.id == 13
	assert pa.raw_id == 3003

@mark.db( template='polar' )
def test_rrrecording( json ):
	json = json['_default']['14']
	pa = PolarActivity( json, 14 )

	# test id
	assert pa['id'] == 14
	assert pa.id == 14
	assert pa.raw_id == 4004


from datetime import datetime
from dateutil.tz import UTC
from dateutil.tz import tzlocal
from tzlocal import get_localzone_name

from pytest import mark

from tracs.activity import Activity
from tracs.activity import Resource
from tracs.activity_types import ActivityTypes
from tracs.dataclasses import as_dict
from tracs.plugins.polar import PolarActivity

@mark.file( 'libraries/default/activities.json' )
def test_init( json ):
	# empty init
	a = Activity()
	assert a['id'] == 0 and a.id == 0

	a = Activity( doc_id=1 )
	assert a['id'] == 1 and a.id == 1

	a = Activity( {'name': 'Run'}, 1 )
	assert a['id'] == 1 and a.id == 1
	assert a.name == 'Run'

	# init from db document
	a = Activity( json['_default']['1'], 1 )

	assert a.doc_id == 1 and a['doc_id'] == 1
	assert a['id'] == 1 and a.id == 1
	assert a.type == "run"
	# assert a.type == ActivityTypes.run

	# times
	assert a.time == '2012-10-24T23:29:40+00:00'
	# assert a.time == datetime( 2012, 1, 7, 10, 40, 56, tzinfo=UTC )
	assert a.localtime == '2012-10-24T22:29:40+01:00'


# assert a.localtime == datetime( 2012, 1, 7, 11, 40, 56, tzinfo=tzlocal() )

@mark.file( 'libraries/default/polar/1/0/0/100001/100001.raw.json' )
def test_init_from( json ):
	src = PolarActivity( json, 2 )
	target = Activity( doc_id=3 )
	target.init_from( src )

	assert target.name == src.name
	assert target.doc_id != src.doc_id


def test_asdict():
	a = Activity()
	assert a.asdict() == {
		'equipment': [],
		'tags'     : [],
		'timezone' : get_localzone_name(),
		'uids'     : []
	}

	assert as_dict( a ) == {
		'equipment': [],
		'tags'     : [],
		'timezone' : get_localzone_name(),
		'uids'     : []
	}

	assert as_dict( a, remove_persist=False ) == {
		'dirty'    : False,
		'doc_id'   : 0,
		'equipment': [],
		'id'       : 0,
		'metadata' : {},
		'resources': [],
		'tags'     : [],
		'timezone' : get_localzone_name(),
		'uids'     : []
	}

	activity_dict = {
		'classifier': 'polar',
		'doc_id'    : 1,
		'id'        : 1,
		'metadata'  : {},
		'name'      : 'name',
		'raw_id'    : 1,
		'resources' : [Resource( name='one', path='one.gpx', status=100, type='gpx' )],
		'time'      : datetime( 2020, 1, 1, 10, 0, 0, tzinfo=UTC ),
		'type'      : ActivityTypes.run,
		'uid'       : 'test:1'
	}

	assert as_dict( Activity( data=activity_dict ) ) == {
		'classifier': 'polar',
#		'metadata'  : {},
#		'resources' : [{
#			'data'    : None,
#			'doc_id'  : 0,
#			'id'      : 0,
#			'name'    : 'one',
#			'path'    : 'one.gpx',
#			'raw'     : None,
#			'raw_data': None,
#			'status'  : 100,
#			'type'    : 'gpx',
#			'uid'     : None
#		}],
		'equipment' : [],
		'name'      : 'name',
		'raw_id'    : 1,
		'tags'      : [],
		'time'      : datetime( 2020, 1, 1, 10, 0, 0, tzinfo=UTC ),
		'timezone'  : get_localzone_name(),
		'type'      : ActivityTypes.run,
		'uid'       : 'test:1',
		'uids'      : []
	}
@
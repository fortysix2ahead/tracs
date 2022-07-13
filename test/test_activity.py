
from datetime import datetime
from dateutil.tz import UTC
from dateutil.tz import tzlocal

from pytest import mark

from tracs.activity import Activity
from tracs.activity import Resource
from tracs.activity_types import ActivityTypes
from tracs.dataclasses import as_dict
from tracs.plugins.polar import PolarActivity

@mark.db( template='default' )
def test_init( json ):
	# empty init
	a = Activity()
	assert a['id'] == 0 and a.id == 0

	a = Activity( doc_id = 1 )
	assert a['id'] == 1 and a.id == 1

	a = Activity( {'name': 'Run' }, 1 )
	assert a['id'] == 1 and a.id == 1
	assert a.name == 'Run'

	# init from db document
	a = Activity( json['_default']['1'], 1 )

	assert a.doc_id == 1 and a['doc_id'] == 1
	assert a['id'] == 1 and a.id == 1
	assert a.type == ActivityTypes.xcski

	# empty_field is in json, but is not declared as attribute
	assert a['empty_field'] is None
	assert 'empty_field' not in a

	# times
	assert a.time == datetime( 2012, 1, 7, 10, 40, 56, tzinfo=UTC )
	assert a.localtime == datetime( 2012, 1, 7, 11, 40, 56, tzinfo=tzlocal() )

@mark.db( template='default' )
def test_init_from( json ):
	src = PolarActivity( json['_default']['2'], 2 )
	target = Activity( doc_id = 3 )
	target.init_from( src )

	assert target.name == src.name
	assert target.doc_id != src.doc_id

def test_asdict():
	a = Activity()
	assert a.asdict() == {
		'resources'       : [],
		'tags'            : [],
	}

	assert as_dict( a ) == {
		'resources': [],
		'tags'     : []
	}

	assert as_dict( a, remove_persist=False ) == {
		'doc_id'      : 0,
		'id'          : 0,
		'resources'   : [],
		'tags'        : [],
		'uids'         : []
	}

	activity_dict = {
		'classifier': 'polar',
		'doc_id'    : 1,
		'groups'    : {},
		'id'        : 1,
		'metadata'  : {},
		'name'      : 'name',
		'raw_id'    : 1,
		'resources' : [Resource( name='one', path='one.gpx', status=100, type='gpx' )],
		'time'      : datetime( 2020, 1, 1, 10, 0, 0, tzinfo=UTC ),
		'type'      : ActivityTypes.run,
		'uid'       : 'polar:1'
	}

	assert as_dict( activity_dict, Activity ) == {
		'classifier': 'polar',
		'groups'    : {},
		'metadata'  : {},
		'resources' : [{
			'name'  : 'one',
			'path'  : 'one.gpx',
			'status': 100,
			'type'  : 'gpx',
			'uid'   : None
		}],
		'name'       : 'name',
		'raw_id'     : 1,
		'time'       : '2020-01-01T10:00:00+00:00',
		'type'       : 'run',
		'uid'        : 'polar:1'
	}

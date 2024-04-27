from datetime import datetime
from json import loads

from dateutil.tz import UTC
from pytest import mark

from core import Metadata
from fsio import load_metadata, load_schema, write_metadata

@mark.context( env='default', persist='mem' )
def test_load_schema( dbfs ):
	assert load_schema( dbfs ).version == 13

@mark.context( env='default', persist='mem' )
def test_load_metadata( dbfs ):
	mds = load_metadata( dbfs )
	assert mds[0].uid == 'polar:1234567890'
	assert mds[0].created == datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC )
	assert mds[0].favourite == True

@mark.context( env='default', persist='mem' )
def test_write_metadata( dbfs ):
	md = Metadata(
		uid='polar:101',
		created=datetime( 2024, 1, 4, 10, 0, 0, tzinfo=UTC ),
		favourite=True,
	)
	write_metadata( [md], dbfs )

	json = loads( dbfs.readtext( 'metadata.json' ) )
	assert json == [ {
		'created': '2024-01-04T10:00:00+00:00',
		'uid': 'polar:101',
		'supplementary': {
			'favourite': True,
		}
	} ]

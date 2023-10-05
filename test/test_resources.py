
from pytest import raises

from tracs.resources import Resource, Resources, ResourceType

def test_resource_type():
	rt = ResourceType( 'application/xml' )
	assert rt == ResourceType( type=rt.type, suffix='xml' ) and rt.extension() == 'xml'

	rt = ResourceType( 'application/gpx+xml' )
	assert rt == ResourceType( type=rt.type, subtype='gpx', suffix='xml' ) and rt.extension() == 'gpx'

	rt = ResourceType( 'application/vnd.polar.flow+json' )
	assert rt == ResourceType( type=rt.type, vendor='polar', subtype='flow', suffix='json' ) and rt.extension() == 'flow.json'

	rt = ResourceType( 'application/vnd.polar+csv' )
	assert rt == ResourceType( type=rt.type, vendor='polar', suffix='csv' ) and rt.extension() == 'csv'

	rt = ResourceType( 'application/vnd.polar.flow+csv' )
	assert rt == ResourceType( type=rt.type, vendor='polar', subtype='flow', suffix='csv' ) and rt.extension() == 'flow.csv'

	rt = ResourceType( 'application/vnd.polar.ped+xml' )
	assert rt == ResourceType( type=rt.type, vendor='polar', subtype='ped', suffix='xml' ) and rt.extension() == 'ped.xml'

	rt = ResourceType( 'application/vnd.polar.gpx+zip' )
	assert rt == ResourceType( type=rt.type, vendor='polar', subtype='gpx', suffix='zip' ) and rt.extension() == 'gpx.zip'

	assert ResourceType( 'application/fit' ).extension() == 'fit'
	assert ResourceType( 'application/vnd.bikecitizens+json' ).extension() == 'json'
	assert ResourceType( 'application/vnd.bikecitizens.rec+json' ).extension() == 'rec.json'
	assert ResourceType( 'application/vnd.polar+json' ).extension() == 'json'
	assert ResourceType( 'application/vnd.strava+json' ).extension() == 'json'
	assert ResourceType( 'application/vnd.waze+txt' ).extension() == 'txt'
	assert ResourceType( 'application/vnd.polar.hrv+txt' ).extension() == 'hrv.txt'
	assert ResourceType( 'application/gpx+xml' ).extension() == 'gpx'
	assert ResourceType( 'application/vnd.polar.ped+xml' ).extension() == 'ped.xml'
	assert ResourceType( 'application/tcx+xml' ).extension() == 'tcx'
	assert ResourceType( 'application/vnd.polar+csv' ).extension() == 'csv'
	assert ResourceType( 'application/vnd.polar.hrv+csv' ).extension() == 'hrv.csv'

def test_resources():

	r1 = Resource( uid='polar:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )
	r2 = Resource( uid='polar:1234', name='test2.gpx', type='application/gpx+xml', path='test2.gpx' )
	r3 = Resource( uid='strava:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )

	resources = Resources()
	resources.add( r1, r2, r3 )

	with raises( KeyError ):
		resources.add( r1 )

	assert r1.id == 1 and r2.id == 2 and r3.id == 3
	assert len( resources ) == len( resources.data )

	assert resources.all() == [r1, r2, r3]
	assert resources.all_for( uid=r1.uid ) == [r1, r2]
	assert resources.all_for( path=r1.path ) == [r1, r3]
	assert resources.all_for( uid=r1.uid, path=r1.path ) == [r1]

	assert list( resources.keys() ) == list( resources.data.keys() )
	assert list( resources.values() ) == list( resources.data.values() )

	key = list( resources.keys() )[0]
	assert resources[key] == resources.data.get( key )
	assert resources.get( key ) == resources.data.get( key )

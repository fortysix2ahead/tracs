from pytest import mark, raises

from tracs.resources import Resource, ResourceList, Resources, ResourceType, ResourceTypes
from tracs.uid import UID

def test_resource_type():
	rt = ResourceType( 'application/xml' )
	assert rt.suffix == 'xml' and rt.extension() == 'xml'

	rt = ResourceType( 'application/gpx+xml' )
	assert rt.subtype == 'gpx' and rt.suffix == 'xml' and rt.extension() == 'gpx'

	rt = ResourceType( 'application/vnd.polar.flow+json' )
	assert rt.subtype == 'flow' and rt.suffix == 'json' and rt.vendor == 'polar' and rt.extension() == 'flow.json'

	rt = ResourceType( 'application/vnd.polar+csv' )
	assert rt.suffix == 'csv' and rt.vendor == 'polar' and rt.extension() == 'csv'

	rt = ResourceType( 'application/vnd.polar.flow+csv' )
	assert rt.subtype == 'flow' and rt.suffix == 'csv' and rt.vendor == 'polar' and rt.extension() == 'flow.csv'

	rt = ResourceType( 'application/vnd.polar.ped+xml' )
	assert rt.subtype == 'ped' and rt.suffix == 'xml' and rt.vendor == 'polar' and rt.extension() == 'ped.xml'

	rt = ResourceType( 'application/vnd.polar.gpx+zip' )
	assert rt.subtype == 'gpx' and rt.suffix == 'zip' and rt.vendor == 'polar' and rt.extension() == 'gpx.zip'

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

def test_resource_types():
	# setup
	ResourceTypes.inst().clear()
	ResourceTypes.inst()[rt.type] = ( rt := ResourceType( 'application/vnd.polar+json', summary=True ) )
	ResourceTypes.inst()[rt.type] = ( rt := ResourceType( 'application/gpx+xml', recording=True ) )
	ResourceTypes.inst()[rt.type] = ( rt := ResourceType( 'image/jpeg', image=True ) )

	# actual test
	assert len( ResourceTypes.inst() ) == 3
	assert ResourceTypes.summaries() == [ ResourceType( 'application/vnd.polar+json', summary=True ) ]
	assert ResourceTypes.recordings() == [ ResourceType( 'application/gpx+xml', recording=True ) ]
	assert ResourceTypes.images() == [ ResourceType( 'image/jpeg', image=True ) ]

def test_resource():
	# creation with separate uid and path arguments
	r = Resource( id=1, name='recording', type='application/gpx+xml', path='recording.gpx', uid='polar:1001' )
	assert r.uid == 'polar:1001'
	assert r.classifier == 'polar'
	assert r.local_id == 1001 and r.local_id_str == '1001'
	assert r.uidpath == 'polar:1001/recording.gpx'

	# path can also be integrated into uid
	r = Resource( id=1, uid='polar:1001/recording.gpx' )
	assert r.uid == 'polar:1001'
	assert r.classifier == 'polar'
	assert r.local_id == 1001 and r.local_id_str == '1001'
	assert r.uidpath == 'polar:1001/recording.gpx'

	# this works, but is not supposed to be used
	r = Resource( uid=UID( classifier='polar', local_id=1001, path='recording.gpx' ) )
	assert r.uid == 'polar:1001' and r.path == 'recording.gpx'

	# resource without a proper uid/path is allowed, this is used by resource handlers which from an external URL
	Resource()
	Resource( path='recording.gpx' )

	with raises( AttributeError ):
		Resource( uid='polar:1001' )
	#with raises( AttributeError ):
	Resource( uid='polar', path='recording.gpx' ) # todo: very special case, not sure what to do with it

@mark.xfail
def test_resource_list():
	r1 = Resource( uid='polar:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )
	r2 = Resource( uid='strava:1234', name='test2.gpx', type='application/gpx+xml', path='test2.gpx' )
	r3 = Resource( uid='polar:1234', name='test1.json', type='application/vnd.polar+json', path='test1.json', summary=True )
	r4 = Resource( uid='strava:1234', name='test2.json', type='application/vnd.polar+json', path='test2.json', summary=True )
	r5 = Resource( uid='polar:1234', name='title.jpg', type='image/jpeg', path='title.jpeg' )

	rl = ResourceList( r1, r2, r3, r4 )
	rl.append( r5 )

	assert len( rl ) == 5

	rl = ResourceList( lst = [r1, r2, r3, r4, r5] )
	assert len( rl ) == 5

	rl = ResourceList( lists = [ResourceList( r1, r2 ), ResourceList( r3, r4, r5 )] )
	assert len( rl ) == 5

	rl = ResourceList.from_list( ResourceList( r1, r2 ), ResourceList( r3, r4, r5 ) )
	assert len( rl ) == 5

	assert rl.all() == [r1, r2, r3, r4, r5]
	assert rl.all_for( uid=r1.uid ) == [r1, r3, r5]
	assert rl.all_for( path=r1.path ) == [r1]
	assert rl.all_for( uid=r1.uid, path=r1.path ) == [r1]

	r1a = Resource( uid='polar:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' ) # copy of r1
	assert r1a in rl
	r1a.path = 'other.gpx'
	assert r1a not in rl

	assert rl.summary() == r3
	assert rl.summaries() == [r4, r5]
	assert rl.recording() == r1
	assert rl.recordings() == [r1, r2, r3]
	assert rl.image() == r5
	assert rl.images() == [r5]

def test_resources():
	r1 = Resource( uid='polar:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )
	r2 = Resource( uid='polar:1234', name='test2.gpx', type='application/gpx+xml', path='test2.gpx' )
	r3 = Resource( uid='strava:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )
	r4 = Resource( uid='polar:1234', name='test1.json', type='application/vnd.polar+json', path='test1.json', summary=True )
	r5 = Resource( uid='polar:1234', name='test2.json', type='application/vnd.polar+json', path='test2.json', summary=True )

	resources = Resources()
	assert resources.add( r1, r2, r3 ) == [1, 2, 3]
	assert resources.__id_map__[1] == r1
	assert resources.__uid_map__[f'{r1.uid}/{r1.path}'] == r1

	with raises( KeyError ):
		resources.add( r1 )

	assert r1.id == 1 and r2.id == 2 and r3.id == 3
	assert len( resources ) == len( resources.data )

	assert resources.all() == [r1, r2, r3]
	assert resources.all_for( uid=r1.uid ) == [r1, r2]
	assert resources.all_for( path=r1.path ) == [r1, r3]
	assert resources.all_for( uid=r1.uid, path=r1.path ) == [r1]

	r1a = Resource( uid='polar:1234', name='test1.gpx', type='application/gpx+xml', path='test1.gpx' )
	assert r1a in resources
	r1a.path = 'other.gpx'
	assert r1a not in resources
	assert 10 not in resources

	assert resources.keys() == [r1.uidpath, r2.uidpath, r3.uidpath]
	assert resources.values() == [r1, r2, r3]
	assert resources.ids() == [1, 2, 3]

	key = list( resources.keys() )[0]
	assert resources[key] == resources.__uid_map__.get( key )
	assert resources.get( key ) == resources.__uid_map__.get( key )

	assert resources.summary() is None
	resources.add( r4, r5 )
	assert resources.summary() == r4
	assert resources.summaries() == [r4, r5]
	assert resources.recordings() == [r1, r2, r3]

	# test update
	r1a = Resource( uid='polar:1234', name='updated.gpx', type='application/gpx+xml', path='test1.gpx' )
	r2a = Resource( uid='polar:1234', name='new.gpx', type='application/gpx+xml', path='new.gpx' )
	assert resources.update( r1a, r2a ) == ([6], [1])
	assert resources.__id_map__[r1.id].name == 'updated.gpx'
	assert r1a.id == r1.id

	# test iteration
	counter = 0
	for r in resources:
		counter += 1
	assert counter == len( resources )

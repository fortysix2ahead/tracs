
from tracs.resources import ResourceType

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

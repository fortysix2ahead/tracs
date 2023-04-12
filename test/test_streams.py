from pytest import mark

from tracs.plugins.gpx import GPX_TYPE
from tracs.registry import Registry
from tracs.streams import Stream

@mark.file( 'templates/gpx/mapbox.gpx' )
def test_gpx_importer( path ):
	resource = Registry.importer_for( GPX_TYPE ).load( path=path )
	stream = Stream( gpx=resource.raw )

	assert stream.length == 206
	
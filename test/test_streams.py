from pytest import mark

from tracs.plugins.gpx import GPX_TYPE
from tracs.registry import Registry
from tracs.streams import Stream

@mark.file( 'templates/gpx/mapbox.gpx' )
def test_gpx_importer( path ):
	resource = Registry.importer_for( GPX_TYPE ).load( path=path )
	stream = Stream( gpx=resource.raw )

	assert stream.length == 206

	gpx = stream.as_gpx()
	assert len( gpx.tracks ) == 1
	assert len( gpx.tracks[0].segments ) == 1
	assert len( gpx.tracks[0].segments[0].points ) == 206

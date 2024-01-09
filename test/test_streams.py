from pytest import mark

from tracs.plugins.gpx import GPXImporter
from tracs.streams import Stream

@mark.file( 'templates/gpx/mapbox.gpx' )
def test_gpx_importer( path ):
	resource = GPXImporter().load( path=path )
	stream = Stream( gpx=resource.raw )

	assert stream.length == 206

	gpx = stream.as_gpx()
	assert len( gpx.tracks ) == 1
	assert len( gpx.tracks[0].segments ) == 1
	assert len( gpx.tracks[0].segments[0].points ) == 206

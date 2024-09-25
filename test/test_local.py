
from __future__ import annotations

from pytest import mark

from logging import getLogger

from plugins.local import Local

log = getLogger( __name__ )

@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import( service ):
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey.zip' )
	activities, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities ) == 13
	assert all( [ a.uid.classifier == 'drivey' for a in activities ] )
	assert all( [ len( a.resources ) == 1 for a in activities ] )

	assert sorted( fs.listdir( 'drivey/24/08' ) ) == ['25', '26', '27', '28']
	assert sorted( fs.listdir( 'drivey/24/08/27/240827145524' ) ) == [ '240827145524.gpx' ]

	# same data, this time from dir
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey' )
	activities, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities ) == 13

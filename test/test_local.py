
from __future__ import annotations

from io import UnsupportedOperation
from logging import getLogger

from pytest import mark, raises

from tracs.aio import import_activities
from tracs.plugins.local import Local

log = getLogger( __name__ )

# noinspection PyUnresolvedReferences
@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import_from_zip( service ):
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey.zip' )
	activities, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities ) == 13
	assert all( [ a.uid.classifier == 'drivey' for a in activities ] )
	assert all( [ len( a.resources ) == 1 for a in activities ] )

	assert sorted( fs.listdir( 'drivey/24/08' ) ) == ['25', '26', '27', '28']
	assert sorted( fs.listdir( 'drivey/24/08/27/240827145524' ) ) == [ '240827145524.gpx' ]
	assert all( [ f.endswith( '.gpx' ) for f in fs.walk.files() ] )

	# test import with a resource already existing

	service.db._activities.add( activities[0] )
	activities2, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities2 ) == 12

	activities2, fs = service.unified_import( service.ctx, classifier='drivey', location=location, force=True )
	assert len( activities2 ) == 13

# noinspection PyUnresolvedReferences

@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import_from_dir( service ):
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey' )
	activities, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities ) == 13
	assert all( [ f.endswith( '.gpx' ) for f in fs.walk.files() ] )

# noinspection PyUnresolvedReferences
@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import_from_file( service ):
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey/drive-20240825-160655.gpx' )
	activities, fs = service.unified_import( service.ctx, classifier='drivey', location=location )
	assert len( activities ) == 1
	assert all( [ f.endswith( '.gpx' ) for f in fs.walk.files() ] )

# noinspection PyUnresolvedReferences
@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import( service ):
	location = service.ctx.config_fs.getsyspath( 'takeouts/drivey.zip' )
	import_activities( service.ctx, [ 'local' ], location=location )

# noinspection PyUnresolvedReferences

@mark.context( env='default', persist='clone', cleanup=True )
@mark.service( cls=Local, init=True, register=True )
def test_unified_import_fail( service ):
	with raises( UnsupportedOperation ):
		activities, fs = service.unified_import( service.ctx, classifier='drivey', location='something_that_does_not_exist' )

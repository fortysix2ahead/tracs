
from gtrac.plugins import load
from gtrac.plugins import Registry

from .fixtures import clean_registry
from .fixtures import setup_registry

def test_load_default( clean_registry, setup_registry ):
	load()

	import gtrac.plugins.base as base
	import gtrac.plugins.bikecitizens as bikecitizens
	import gtrac.plugins.empty as empty
	import gtrac.plugins.polar as polar
	import gtrac.plugins.strava as strava
	import gtrac.plugins.waze as waze

	accessor_count = len( base.accessors() )
	accessor_count += len( bikecitizens.accessors() )
	accessor_count += len( empty.accessors() )
	accessor_count += len( polar.accessors() )
	accessor_count += len( strava.accessors() )
	accessor_count += len( waze.accessors() )

	assert len( Registry.accessors ) == accessor_count + 1 # +1 because one accessor is defined with @accessor ...

	assert sorted( list( Registry.accessors_for( None ).keys() ) ) == sorted( ['_classifier', 'id', 'uid'] )
	assert list( Registry.transformers_for( None ).keys() ) == ['time', 'localtime', 'type']

	assert list( Registry.accessors_for( 'empty' ).keys() ) == ['id', 'uid', 'raw_id', 'type']
	assert list( Registry.transformers_for( 'empty' ).keys() ) == []

# this fails when run after load(), probably because the decorators are only called once
def _test_load_base( clean_registry ):
	load( disabled=[ 'bikecitizens', 'polar', 'strava', 'waze' ] )

	import gtrac.plugins.base as base
	import gtrac.plugins.empty as empty

	accessor_count = len( base.accessors() )
	accessor_count += len( empty.accessors() )

	assert len( Registry.accessors ) == accessor_count

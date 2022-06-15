
from tracs.plugins import load
from tracs.plugins import Registry

from .fixtures import clean_registry
from .fixtures import setup_registry

def test_load_default( clean_registry, setup_registry ):
	load()

	import tracs.plugins.base as base
	import tracs.plugins.bikecitizens as bikecitizens
	import tracs.plugins.empty as empty
	import tracs.plugins.polar as polar
	import tracs.plugins.strava as strava
	import tracs.plugins.waze as waze

	accessor_count = len( base.accessors() )
	accessor_count += len( bikecitizens.accessors() )
	accessor_count += len( empty.accessors() )
	accessor_count += len( polar.accessors() )
	accessor_count += len( strava.accessors() )
	accessor_count += len( waze.accessors() )

	assert len( Registry.accessors ) == accessor_count + 1 # +1 because one accessor is defined with @accessor ...

	assert sorted( list( Registry.accessors_for( None ).keys() ) ) == sorted( ['classifier', 'id', 'uid'] )
	assert list( Registry.transformers_for( None ).keys() ) == ['time', 'localtime', 'type']

	assert list( Registry.accessors_for( 'empty' ).keys() ) == ['id', 'uid', 'raw_id', 'type']
	assert list( Registry.transformers_for( 'empty' ).keys() ) == []

# this fails when run after load(), probably because the decorators are only called once
def _test_load_base( clean_registry ):
	load( disabled=[ 'bikecitizens', 'polar', 'strava', 'waze' ] )

	import tracs.plugins.base as base
	import tracs.plugins.empty as empty

	accessor_count = len( base.accessors() )
	accessor_count += len( empty.accessors() )

	assert len( Registry.accessors ) == accessor_count

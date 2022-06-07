from typing import Mapping
from typing import Tuple

from pytest import fixture

from gtrac.db import ActivityDb
from gtrac.plugins import Registry
from .helpers import get_db_json

@fixture
def db_default_inmemory() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'default', True )

@fixture
def db_default_file() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'default', False )

@fixture
def clean_registry():
	Registry.accessors.clear()
	Registry.transformers.clear()
	Registry.writers.clear()

	Registry.services.clear()
	Registry.service_classes.clear()
	Registry.document_classes.clear()

	Registry.downloaders = {}
	Registry.fetchers = {}

@fixture
def setup_registry():
	import gtrac.plugins.base as base
	Registry.register_accessors( None, base.accessors() )
	Registry.register_transformers( None, base.transformers() )
	Registry.register_function( '_classifier', base._classifier, Registry.accessors )

	import gtrac.plugins.bikecitizens as bikecitizens
	Registry.register_accessors( 'bikecitizens', bikecitizens.accessors() )
	Registry.register_transformers( 'bikecitizens', bikecitizens.transformers() )

	import gtrac.plugins.empty as empty
	Registry.register_accessors( 'empty', empty.accessors() )
	Registry.register_transformers( 'empty', empty.transformers() )

	import gtrac.plugins.polar as polar
	Registry.register_accessors( 'polar', polar.accessors() )
	Registry.register_transformers( 'polar', polar.transformers() )

	import gtrac.plugins.strava as strava
	Registry.register_accessors( 'strava', strava.accessors() )
	Registry.register_transformers( 'strava', strava.transformers() )

	import gtrac.plugins.waze as waze
	Registry.register_accessors( 'waze', waze.accessors() )
	Registry.register_transformers( 'waze', waze.transformers() )

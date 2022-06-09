from pathlib import Path
from typing import Mapping
from typing import Tuple

from pytest import fixture

from tracs.db import ActivityDb
from tracs.plugins import Registry
from .helpers import get_db_json
from .helpers import var_run_path


@fixture
def db_default_inmemory() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'default', True )

@fixture
def db_default_file() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'default', False )

@fixture
def db_empty_inmemory() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'empty', True )

@fixture
def db_empty_file() -> Tuple[ActivityDb, Mapping]:
	return get_db_json( 'empty', False )

@fixture
def var_dir() -> Path:
	return var_run_path()

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
	import tracs.plugins.base as base
	Registry.register_accessors( None, base.accessors() )
	Registry.register_transformers( None, base.transformers() )
	Registry.register_function( '_classifier', base._classifier, Registry.accessors )

	import tracs.plugins.bikecitizens as bikecitizens
	Registry.register_accessors( 'bikecitizens', bikecitizens.accessors() )
	Registry.register_transformers( 'bikecitizens', bikecitizens.transformers() )

	import tracs.plugins.empty as empty
	Registry.register_accessors( 'empty', empty.accessors() )
	Registry.register_transformers( 'empty', empty.transformers() )

	import tracs.plugins.polar as polar
	Registry.register_accessors( 'polar', polar.accessors() )
	Registry.register_transformers( 'polar', polar.transformers() )

	import tracs.plugins.strava as strava
	Registry.register_accessors( 'strava', strava.accessors() )
	Registry.register_transformers( 'strava', strava.transformers() )

	import tracs.plugins.waze as waze
	Registry.register_accessors( 'waze', waze.accessors() )
	Registry.register_transformers( 'waze', waze.transformers() )

from datetime import datetime, timedelta
from typing import Optional

from pytest import mark, raises

from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, resourcetype
from tracs.registry import Registry
from tracs.resources import ResourceType

def setup_module( module ):
	# noinspection PyUnresolvedReferences
	import tracs.plugins.rule_extensions

# test cases

@resourcetype( type='application/one', summary=True )
class ActivityOne:
	pass

@resourcetype( type='application/two' )
class ActivityTwo:
	pass

class ActivityThree:
	pass

@mark.resource_type( types=('application/one', 'application/two'), default=False )
def test_resource_type( registry: Registry ):
	assert 'application/one' in registry.resource_types.keys()
	assert registry.resource_types['application/one'] == ResourceType( type='application/one', summary=True )

	assert 'application/two' in registry.resource_types.keys()
	assert registry.resource_types['application/two'] == ResourceType( type='application/two', summary=False )

	registry.register_resource_type( ResourceType( type='application/three' ) )

	rt = registry.resource_type_for_extension( 'one' )
	assert rt == registry.resource_types['application/one']

# plain importer without any specific resource type information
@importer
class ImporterOne( ResourceHandler ):
	TYPE = 'TYPE_1'

# allowed: define type via decorator
@importer( type='TYPE_2' )
class ImporterTwo( ResourceHandler ):
	pass

def test_importer( registry: Registry ):
	assert type( registry.importer_for( 'TYPE_1' ) ) == ImporterOne
	assert type( registry.importer_for( 'TYPE_2' ) ) == ImporterTwo

def test_fields_and_types( registry ):
	assert (f := registry.activity_field( 'name' )) is not None and f.type in [str, 'str']
	assert (f := registry.activity_field( 'id' )) is not None and f.type in [int, 'int']
	assert (f := registry.activity_field( 'distance' )) is not None and f.type in [float, 'float']
	assert (f := registry.activity_field( 'duration' )) is not None and f.type in [timedelta, 'timedelta']
	assert (f := registry.activity_field( 'starttime' )) is not None and f.type in [datetime, 'datetime']

#	with raises( AttributeError ):
	assert registry.activity_field( 'not_existing_field' ) is None

	# check above fields against normalizers
	assert registry.rule_normalizer_type( 'name' ) in [str, 'str']
	assert registry.rule_normalizer_type( 'id' ) in [int, 'int']
	assert registry.rule_normalizer_type( 'distance' ) in [float, 'float']
	assert registry.rule_normalizer_type( 'duration' ) in [timedelta, 'timedelta']
	assert registry.rule_normalizer_type( 'time' ) in [datetime, 'datetime']

	assert registry.rule_normalizer_type( 'not_existing_field' ) is None

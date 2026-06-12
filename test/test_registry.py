from datetime import datetime, timedelta

from pytest import mark

from tracs.handlers import ResourceHandler
from tracs.pluginmgr import importer, Registry, resource_type
from tracs.resources import ResourceType

# test cases

# resource types

RT_ONE = ResourceType( name='application/one', summary=True )
RT_TWO = ResourceType( name='application/two', recording=True )

@resource_type
def resource_type_one() -> ResourceType:
	return RT_ONE

@resource_type
def resource_type_two() -> ResourceType:
	return RT_TWO

@mark.resource_type( types=('application/one', 'application/two'), default=False )
def test_resource_type( registry: Registry ):
	assert 'application/one' in [ r.name for r in registry.resource_types() ]
	assert registry.resource_type( 'application/one' ) == RT_ONE

	assert 'application/two' in [ r.name for r in registry.resource_types() ]
	assert registry.resource_type( 'application/two' ) == RT_TWO

	assert registry.resource_type_for_extension( 'one' ) == RT_ONE

# importers

# plain importer without any specific resource type information
@importer
class ImporterOne( ResourceHandler ):
	TYPE = 'TYPE_1'

# allowed: define type via decorator
@importer( type='TYPE_2' )
class ImporterTwo( ResourceHandler ):
	pass

def test_importer( registry: Registry ):
	assert type( registry.importer( 'TYPE_1' ) ) == ImporterOne
	assert type( registry.importer( 'TYPE_2' ) ) == ImporterTwo

# activity fields

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

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
	assert 'application/one' in [ r.name for r in registry.resource_types ]
	assert registry.resource_type( 'application/one' ) == RT_ONE

	assert 'application/two' in [ r.name for r in registry.resource_types ]
	assert registry.resource_type( 'application/two' ) == RT_TWO

	assert registry.resource_type_for_extension( 'one' ) == RT_ONE

# importers

# plain importer without any specific resource type information
@importer
class ImporterOne( ResourceHandler ):
	TYPE = RT_ONE.name

# allowed: define type via decorator
@importer( type=RT_TWO.name )
class ImporterTwo( ResourceHandler ):
	pass

def test_importer( registry: Registry ):
	assert type( registry.importer( RT_ONE.name ) ) == ImporterOne
	assert type( registry.importer( RT_TWO.name ) ) == ImporterTwo

# activity fields

def test_derived_fields( registry ):
	assert (f := registry.derived_field( 'day' )) is not None and f.type in [int, 'int']
	assert (f := registry.derived_field( 'weekday' )) is not None and f.type in [int, 'int']
	assert (f := registry.derived_field( 'month' )) is not None and f.type in [int, 'int']
	assert (f := registry.derived_field( 'year' )) is not None and f.type in [int, 'int']

	assert registry.derived_field( 'not_existing_field' ) is None

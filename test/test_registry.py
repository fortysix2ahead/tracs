
from pytest import raises

from tracs.handlers import ResourceHandler
from tracs.registry import importer
from tracs.registry import Registry
from tracs.registry import resourcetype
from tracs.resources import ResourceType

@resourcetype( type='application/one', summary=True )
class ActivityOne:
	pass

@resourcetype( type='application/two' )
class ActivityTwo:
	pass

class ActivityThree:
	pass

def test_resource_type():
	assert 'application/one' in Registry.resource_types.keys()
	assert Registry.resource_types['application/one'] == ResourceType( type='application/one', suffix='one', summary=True, activity_cls=ActivityOne )

	assert 'application/two' in Registry.resource_types.keys()
	assert Registry.resource_types['application/two'] == ResourceType( type='application/two', suffix='two', summary=False, activity_cls=ActivityTwo )

	Registry.register_resource_type( ResourceType( type='application/three', activity_cls=ActivityThree ) )
	assert Registry.resource_types.get( 'application/three' ).activity_cls is ActivityThree

	rt = Registry.resource_type_for_extension( 'one' )
	assert rt == Registry.resource_types['application/one']

def test_importer2():

	# importer without type is not allowed
	with raises( RuntimeError ):
		@importer
		class ImporterWithoutArgs( ResourceHandler ):
			pass

	# this is also not possible: without kwargs there is no way to identify the caller ...
	with raises( RuntimeError ):
		@importer( 'TYPE_2' )
		class ImporterWithArgsOnly( ResourceHandler ):
			pass

	# plain importer without any specific resource type information

	@importer( type='TYPE_1' )
	class ImporterOne( ResourceHandler ):
		pass

	assert type( Registry.importer_for( 'TYPE_1' ) ) == ImporterOne

	@importer( type='TYPE_2', activity_cls=ActivityThree, summary=True )
	class ImporterTwo( ResourceHandler ):
		pass

	assert type( Registry.importer_for( 'TYPE_2' ) ) == ImporterTwo
	assert Registry.resource_types.get( 'TYPE_2' ) == ResourceType( type='TYPE_2', activity_cls=ActivityThree, summary=True )

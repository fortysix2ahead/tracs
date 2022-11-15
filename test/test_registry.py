
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

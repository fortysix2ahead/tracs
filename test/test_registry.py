from datetime import datetime, timedelta
from typing import Optional

from pytest import raises

from tracs.handlers import ResourceHandler
from tracs.registry import importer
from tracs.registry import Registry
from tracs.registry import resourcetype
from tracs.resources import ResourceType

def setup_module( module ):
	# noinspection PyUnresolvedReferences
	import tracs.plugins.rule_extensions

# sample code for generic decorating:

def decorator_with_args( *args, **kwargs ):
	def decorator( func ):
		def wrapper( *wrapper_args, **wrapper_kwargs ):
			func( *wrapper_args, **wrapper_kwargs )
		if args and not kwargs:
			print( 'with args only' )
		elif not args and kwargs:
			print( 'with kwargs only' )
		elif args and kwargs:
			print( 'with args and kwargs' )
		return wrapper

	if args and not kwargs and callable( args[0] ):
		print( 'without arguments' )
	return decorator

def real_decorator( *args, **kwargs ):
	return decorator_with_args( *args, **kwargs )

@real_decorator
def one():
	pass

@real_decorator( 'some value', 'some other value' )
def two():
	pass

@real_decorator( kwarg_one='some value', kwarg_two='some other value' )
def three():
	pass

@real_decorator( 'some value', 'some other value', kwarg_one='some value', kwarg_two='some other value' )
def four():
	pass

# test cases

@resourcetype( type='application/one', summary=True )
class ActivityOne:
	pass

@resourcetype( type='application/two' )
class ActivityTwo:
	pass

class ActivityThree:
	pass

def test_resource_type():
	assert 'application/one' in Registry.instance().resource_types.keys()
	assert Registry.instance().resource_types['application/one'] == ResourceType( type='application/one', suffix='one', summary=True, activity_cls=ActivityOne )

	assert 'application/two' in Registry.instance().resource_types.keys()
	assert Registry.instance().resource_types['application/two'] == ResourceType( type='application/two', suffix='two', summary=False, activity_cls=ActivityTwo )

	Registry.register_resource_type( ResourceType( type='application/three', activity_cls=ActivityThree ) )
	assert Registry.instance().resource_types.get( 'application/three' ).activity_cls is ActivityThree

	rt = Registry.resource_type_for_extension( 'one' )
	assert rt == Registry.instance().resource_types['application/one']

def test_importer2():

	# importer without type is not allowed
	with raises( ValueError ):
		@importer
		class ImporterWithoutArgs( ResourceHandler ):
			pass

	# this is also not possible: don't allow non-kwargs
	with raises( TypeError ):
		@importer( 'TYPE_2' )
		class ImporterWithArgsOnly( ResourceHandler ):
			pass

	print()

	# plain importer without any specific resource type information
	@importer
	class ImporterOne( ResourceHandler ):
		TYPE = 'TYPE_1'

	assert type( Registry.importer_for( 'TYPE_1' ) ) == ImporterOne

	# allowed: define type via decorator, but bad for testing
	@importer( type='TYPE_2' )
	class ImporterTwo( ResourceHandler ):
		pass

	assert type( Registry.importer_for( 'TYPE_2' ) ) == ImporterTwo

def test_fields_and_types( keywords ):
	assert (f := Registry.activity_field( 'name' )) is not None and f.type == Optional[str]
	assert (f := Registry.activity_field( 'id' )) is not None and f.type == int
	assert (f := Registry.activity_field( 'distance' )) is not None and f.type == Optional[float]
	assert (f := Registry.activity_field( 'duration' )) is not None and f.type == Optional[timedelta]
	assert (f := Registry.activity_field( 'starttime' )) is not None and f.type == datetime
	assert Registry.activity_field( 'not_existing_field' ) is None

	# check above fields against normalizers
	assert Registry.rule_normalizer_type( 'name' ) == Optional[str]
	assert Registry.rule_normalizer_type( 'id' ) == int
	assert Registry.rule_normalizer_type( 'distance' ) == Optional[float]
	assert Registry.rule_normalizer_type( 'duration' ) == Optional[timedelta]
	assert Registry.rule_normalizer_type( 'time' ) == datetime
	assert Registry.rule_normalizer_type( 'not_existing_field' ) is None

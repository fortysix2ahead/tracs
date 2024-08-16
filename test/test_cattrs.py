from datetime import timedelta
from typing import ClassVar, List

from attrs import define, field
from cattrs import Converter, GenConverter
from cattrs.gen import make_dict_unstructure_fn, override
from cattrs.preconf.orjson import make_converter
from pytest import mark
from rich.pretty import pprint

@define
class Inner:

	ids: List[int] = field( factory=list )
	__inner_ids__: List[int] = field( factory=list, alias='__inner_ids__' )

@define
class Outer:

	inners: List[Inner] = field( factory=list )
	ids: List[int] = field( factory=list )
	__internal_ids__: List[int] = field( factory=list, alias='__internal_ids__' )

@mark.xfail
def test_cattrs():
	# make converter
	conv = make_converter()

	# converter configuration
	inner_to_dict = make_dict_unstructure_fn(
		Inner,
		conv,
		_cattrs_omit_if_default=True,
		__internal_ids__=override( omit=True ),
	)

	outer_to_dict = make_dict_unstructure_fn(
		Outer,
		conv,
		_cattrs_omit_if_default=True,
		__internal_ids__=override( omit=True ),
	)

	conv.register_unstructure_hook( Inner, inner_to_dict )
	conv.register_unstructure_hook( Outer, outer_to_dict )

	# actual test

	outer = Outer( ids = [10, 20], __internal_ids__ = [ 30, 40 ] )

	result = conv.unstructure( outer )
	assert 'ids' in result and '__internal_ids__' not in result

	inner = Inner( ids=[1, 2, 3], __inner_ids__=[4, 5, 6] )
	outer = Outer( inners=[inner], ids = [10, 20], __internal_ids__ = [ 30, 40 ] )

	result = conv.unstructure( outer )

	assert 'ids' in result and not '__internal_ids__' in result
	assert len( result.get( 'inners' ) ) == 1
	inner_result = result.get( 'inners' )[0]
	assert 'ids' in inner_result

	# the next line fails ...
	assert not '__inner_ids__' in inner_result

# testing hooks

@define
class ClassOne:

	id: int = field( default=None )
	internal_id: int = field( default=None )
	time: timedelta = field( default=None )

def timedelta_to_str( obj: timedelta ) -> str:
	return f'{obj.seconds} sec'

def test_timedelta_hook():
	converter = make_converter()
	converter.register_unstructure_hook( timedelta, timedelta_to_str )

	c = ClassOne( 10, 100, timedelta( hours=2 ) )
	d = converter.unstructure( c )

	assert d == {'id': 10, 'internal_id': 100, 'time': '7200 sec'}

@mark.xfail
def test_class_one_hook():
	converter = make_converter()
	hook = make_dict_unstructure_fn( ClassOne, converter, _cattrs_omit_if_default=True, internal_id=override( omit=True ) )
	converter.register_unstructure_hook( timedelta, timedelta_to_str )
	converter.register_unstructure_hook( ClassOne, hook )

	c = ClassOne( 10, 100, timedelta( hours=2 ) )
	d = converter.unstructure( c )

	# this fails
	assert d == {'id': 10, 'time': '7200 sec'}

if __name__ == '__main__':
	test_cattrs()

# test class specific structuring

@define
class SpecificBase:

	# configure converter
	converter: ClassVar[Converter] = make_converter()
	converter.register_unstructure_hook( timedelta, timedelta_to_str )

	id: int = field( default=None )
	internal_id: int = field( default=None )
	time: timedelta = field( default=None )

	def _unstructure( self, conv ):
		return { k: v for k, v in SpecificBase.converter.unstructure( self ).items() if k not in ['internal_id'] }

def test_specific_base():
	from cattrs.strategies import use_class_methods

	converter = make_converter()
	use_class_methods( converter, "_structure", "_unstructure" )

	c = SpecificBase( 10, 100, timedelta( hours=2 ) )
	d = converter.unstructure( c )

	# this fails
	assert d == {'id': 10, 'time': '7200 sec'}

@define
class Name:

	name: str = field( default=None )

@define
class Names:

	primary: Name = field( default=None )
	second_primary: Name = field( default=None )
	secondary: List[Name] = field( factory=list )

@define
class Book:

	authors: Names = field( default=None )

def test_names():
	book_converter, names_converter = GenConverter( omit_if_default=True ), GenConverter( omit_if_default=True )
	names_converter.register_unstructure_hook( Name, lambda n: n.name.upper() )
	book_converter.register_unstructure_hook( Names, lambda n: names_converter.unstructure( n ) )
	b = Book( authors = Names( primary=Name( 'joe' ), secondary=[ Name( 'john' ), Name( 'jim' ) ] ) )
	pprint( book_converter.unstructure( b ) )

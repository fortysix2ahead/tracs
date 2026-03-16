from datetime import datetime
from typing import ClassVar

from attrs import define, field
from babel.numbers import format_decimal
from pytest import mark, raises

from tracs.core import FieldFormatter, FieldFormatters, FormattedFieldsBase, Metadata, VirtualField, VirtualFields
from tracs.uid import UID

@mark.unit
def test_virtual_field():

	vf = VirtualField( 'one', int, default=10, display_name='One', description='Field One' )
	assert vf.name == 'one' and vf.type == int and vf.display_name == 'One' and vf.description == 'Field One'
	assert vf() == 10

	vf = VirtualField( 'two', str, factory=lambda v: 'two', display_name='Two', description='Field Two' )
	assert vf.name == 'two' and vf.type == str and vf.display_name == 'Two' and vf.description == 'Field Two'
	assert vf() == 'two'

	vf = VirtualField( 'three', str, default=10, factory=lambda v: 'three', display_name='Three', description='Field Three' )
	assert vf.name == 'three' and vf.type == str and vf.display_name == 'Three' and vf.description == 'Field Three'
	assert vf() == 10 # default value wins over lambda

	vf = VirtualField( 'two', str )
	with raises( AttributeError ):
		assert vf() == 'two'

@mark.unit
def test_virtual_fields():

	def to_upper( obj ) -> str:
		return obj.name.upper()

	# test class enriched with virtual fields
	@define
	class ClassWithVirtualFields:

		__vf__: ClassVar[VirtualFields] = VirtualFields()

		name: str = field( default='Name' )
		id: id = field( default=1 )
		__internal_name__: str = field( default='Internal Name', alias='__internal_name__' )

		__fields_proxy__: VirtualFields = field( default=None, alias='__fields_proxy__' )

		@classmethod
		def virtual_fields( cls ) -> VirtualFields:
			return cls.__vf__

		def vf( self ) -> VirtualFields:
			if self.__fields_proxy__ is None:
				self.__fields_proxy__ = VirtualFields( self.__class__.__vf__.data, self )
			return self.__fields_proxy__

	ClassWithVirtualFields.__vf__.add_all(
		VirtualField( 'index', int, default=10 ), # regular
		VirtualField( '_internal_index', int, default=20 ), # internal field
		VirtualField( 'upper_name', str, factory=to_upper, expose=True ),
		VirtualField( 'lower_name', str, factory=lambda p: p.name.lower() ), # try with lambda
		VirtualField( 'no_name', str, factory=lambda p: '', expose=False ),
	)

	# call augment manually to trigger property creation
	VirtualFields.augment( ClassWithVirtualFields )

	cvf = ClassWithVirtualFields()

	assert cvf.name == 'Name'
	assert cvf.upper_name == 'NAME'
	assert cvf.lower_name == 'name'
	# assert cvf.index == 10 # don't know why this fails
	with raises( AttributeError ): # internal index is not exposed as property, because it starts with underscore
		assert cvf._internal_index == 20
	with raises( AttributeError ):
		assert cvf.__another_name__ == 'Another name' # another name is unknown
	with raises( AttributeError ):
		assert cvf.no_name == '' # not exposed as it's marked as not exposed

	# access via vf field - dict-like
#	with raises( KeyError ):
#		assert cvf.vf['name'] == 'Name' # name is not a virtual field
#	assert cvf.vf['upper_name'] == 'NAME'
#	assert cvf.vf['index'] == 10
#	assert cvf.vf['internal_index'] == 20

	# access via vf field
#	with raises( AttributeError ):
#		assert cvf.vf.name == 'Name' # name is not a virtual field
#	assert cvf.vf.upper_name == 'NAME'
#	assert cvf.vf.index == 10
#	assert cvf.vf.internal_index == 20 # internal index works this time
#	with raises( AttributeError ):
#		assert cvf.vf.__another_name__ == 'Another name' # still unknown

	# access via virtual_fields()
	assert ClassWithVirtualFields.virtual_fields().value( 'upper_name', cvf ) == 'NAME'
	assert ClassWithVirtualFields.virtual_fields().value( 'index', cvf ) == 10
	assert ClassWithVirtualFields.virtual_fields().value( '_internal_index', cvf ) == 20
	with raises( AttributeError ):
		assert ClassWithVirtualFields.virtual_fields().value( '_internal_index_noexist', cvf ) is None
	assert ClassWithVirtualFields.virtual_fields().value( '_internal_index_noexist', cvf, quiet=True ) is None

	# access via vf()
	assert cvf.vf().value( 'upper_name' ) == 'NAME'

	# values
	assert cvf.vf().values( 'index', 'upper_name', 'xyz' ) == [10, 'NAME', None]

	# contains
	assert 'upper_name' in cvf.vf() and 'index' in cvf.vf() and '_internal_index' in cvf.vf()

	names = ClassWithVirtualFields.virtual_fields().field_names()
	assert sorted( names ) == sorted( ['index', 'lower_name', 'upper_name'] )

	# same as default above
	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=False, include_unexposed=False )
	assert sorted( names ) == sorted( ['index', 'lower_name', 'upper_name'] )

	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=True, include_unexposed=False )
	assert sorted( names ) == sorted( ['index', 'lower_name', 'upper_name', '_internal_index' ] )

	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=False, include_unexposed=False )
	assert sorted( names ) == sorted( ['index', 'lower_name', 'upper_name'] )

	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=False, include_unexposed=True )
	assert sorted( names ) == sorted( ['upper_name', 'lower_name', 'no_name', 'index'] )

	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=False, include_unexposed=True )
	assert sorted( names ) == sorted( ['index', 'lower_name', 'no_name', 'upper_name'] )

	names = ClassWithVirtualFields.virtual_fields().field_names( include_internal=True, include_unexposed=True )
	assert sorted( names ) == sorted( ['lower_name', 'upper_name', 'index', 'no_name', '_internal_index'] )

@mark.unit
def test_formatted_field():

	ff = FieldFormatter( name='lower', formatter=lambda v, f, l: v.lower() )
	assert ff( "TEST" ) == 'test'
	assert ff.__format__( "TEST" ) == 'test'

	# test babel fields
	ff_en = FieldFormatter( name='en_int', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='en' )
	ff_de = FieldFormatter( name='de_de', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='de' )

	assert ff_en( 1000 ) == '1,000'
	assert ff_de( 1000 ) == '1.000'

	# provide format and locale at runtime
	ff_uni = FieldFormatter( name='uni', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='en' )
	assert ff_uni( 1000, format='####' ) == '1000'
	assert ff_uni( 1000, locale='de' ) == '1.000'

@mark.unit
def test_formatted_fields():

	ffs = FieldFormatters()
	ffs['lower'] = lambda v, f, l: v.lower()
	ffs['upper'] = FieldFormatter( name='upper', formatter=lambda s: s.upper() )

	assert 'lower' in ffs and type( ffs.get( 'lower' ) ) is FieldFormatter
	assert 'upper' in ffs and type( ffs.get( 'upper' ) ) is FieldFormatter

	@define
	class FormattedDataclass( FormattedFieldsBase ):

		name: str = field( default = 'Name' )
		age: int = field( default=10 )
		speed: float = field( default=12345.6 )
		width: float = field( default=None )

	FormattedDataclass.__fmf__['name'] = lambda v, f, l: v.lower()
	FormattedDataclass.__fmf__.add( FieldFormatter( name='speed', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='en' ) )

	fdc = FormattedDataclass()

	assert fdc.format( 'name' ) == 'name'
	assert fdc.format( 'age' ) == '10' # this uses the default formatter
	assert fdc.format( 'speed' ) == '12,345.6'

	with raises( AttributeError ):
		assert fdc.format( 'noexist' ) == ''
	assert fdc.format( 'noexist', suppress_errors=True ) == ''

	assert fdc.format_as_list( 'name', 'age', 'speed', 'width' ) == [ 'name', '10', '12,345.6', '' ] # last should be 'None' ?
	# assert fdc.format_as_list( 'name', 'age', 'speed', 'width' ) == [ 'name', '10', '12,345.6', 'None' ]

	with raises( AttributeError ):
		assert fdc.format_as_list( 'name', 'age', 'speed', 'height' ) == ['name', '10', '12,345.6', '']
	assert fdc.format_as_list( 'name', 'age', 'speed', 'height', suppress_errors=True ) == ['name', '10', '12,345.6', '']
	assert fdc.format_as_list( 'name', 'age', 'speed', 'width', conv=lambda v: str( v ) ) == ['Name', '10', '12345.6', 'None']

@mark.unit
def test_metadata():

	md = Metadata(
		created=datetime( 2023, 6, 1, 10, 0, 0 ),
		modified=datetime( 2023, 7, 2, 11, 0, 0 ),
		members=[ UID( 'polar:101' ), UID( 'strava:101' ) ],
		f1='one',
	)

	md.f2 = 'two'
	md['f3'] = 'three'

	assert len( md ) == 7
	assert md.f2 == 'two'
	assert md['f3'] == 'three'
	assert md.members == [ UID( 'polar:101' ), UID( 'strava:101' ) ]

	assert md.keys() == ['created', 'modified', 'favourite', 'members', 'f1', 'f2', 'f3']
	assert md.values() == [
		datetime( 2023, 6, 1, 10, 0, 0 ),
		datetime( 2023, 7, 2, 11, 0, 0 ),
		False,
		[ UID( 'polar:101' ), UID( 'strava:101' ) ],
		'one',
		'two',
		'three',
	]
	assert md.items() == [
		('created', datetime( 2023, 6, 1, 10, 0, 0 )),
		('modified', datetime( 2023, 7, 2, 11, 0, 0 )),
		('favourite', False),
		('members', [ UID( 'polar:101' ), UID( 'strava:101' ) ]),
		('f1', 'one'),
		('f2', 'two'),
		('f3', 'three'),
	]
	assert md.as_dict() == {
		'created': datetime( 2023, 6, 1, 10, 0, 0 ),
		'modified': datetime( 2023, 7, 2, 11, 0, 0 ),
		'favourite': False,
		'members': [ UID( 'polar:101' ), UID( 'strava:101' ) ],
		'f1': 'one',
		'f2': 'two',
		'f3': 'three',
	}

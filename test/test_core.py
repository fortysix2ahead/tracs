from attrs import define, field
from babel.numbers import format_decimal
from pytest import raises

from tracs.core import FormattedField, FormattedFields, FormattedFieldsBase, VirtualField, VirtualFields, VirtualFieldsBase

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

def test_virtual_fields():

	# test class enriched with virtual fields
	@define
	class EnrichedDataclass( VirtualFieldsBase ):

		name: str = field( default='Name' )
		__internal_name__ = field( default='Internal Name', alias='__internal_name__' )

	vf = EnrichedDataclass.__vf__

	vf['index'] = VirtualField( 'index', int, default=10 )
	vf.add( VirtualField( 'upper_name', str, factory=lambda *args: args[0].name.upper() ) )

	edc = EnrichedDataclass()
	assert edc.name == 'Name'
	assert edc.vf.upper_name == 'NAME'
	assert edc.vf.index == 10

	assert 'index' in edc.vf and 'upper_name' in edc.vf

	assert EnrichedDataclass.field_names() == [ 'name', '__internal_name__' ]
	assert EnrichedDataclass.field_names( False ) == [ 'name' ]
	assert EnrichedDataclass.field_names( True ) == [ 'name', '__internal_name__' ]
	assert EnrichedDataclass.field_names( True, True ) == [ 'name', '__internal_name__', 'index', 'upper_name' ]
	assert EnrichedDataclass.field_names( False, True ) == [ 'name', 'index', 'upper_name' ]

def test_formatted_field():

	ff = FormattedField( name='lower', formatter=lambda v, f, l: v.lower() )
	assert ff( "TEST" ) == 'test'
	assert ff.__format__( "TEST" ) == 'test'

	# test babel fields
	ffe = FormattedField( name='en_int', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='en' )
	ffd = FormattedField( name='en_de', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='de' )

	assert ffe( 1000 ) == '1,000'
	assert ffd( 1000 ) == '1.000'

def test_formatted_fields():

	ffs = FormattedFields()
	ffs['lower'] = lambda v, f, l: v.lower()
	ffs['upper'] = FormattedField( name='upper', formatter=lambda s: s.upper() )

	assert 'lower' in ffs.__fields__ and type( ffs.__fields__.get( 'lower' ) ) is FormattedField
	assert 'upper' in ffs.__fields__ and type( ffs.__fields__.get( 'upper' ) ) is FormattedField

	@define
	class FormattedDataclass( FormattedFieldsBase ):

		name: str = field( default = 'Name' )

	FormattedDataclass.__fmf__['name'] = lambda v, f, l: v.lower()

	fdc = FormattedDataclass()

	assert fdc.fmf.name == 'name'

	with raises( AttributeError ):
		assert fdc.fmf.noexist == 0

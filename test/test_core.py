from typing import ClassVar

from attrs import define, field, fields
from pytest import raises

from tracs.core import FormattedField, FormattedFields, VirtualField, VirtualFields, VirtualFieldsBase

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

	vf = EnrichedDataclass.__vf__

	vf['index'] = VirtualField( 'index', int, default=10 )
	vf.add( VirtualField( 'upper_name', str, factory=lambda *args: args[0].name.upper() ) )

	edc = EnrichedDataclass()
	assert edc.name == 'Name'
	assert edc.vf.upper_name == 'NAME'
	assert edc.vf.index == 10

	assert 'index' in edc.vf and 'upper_name' in edc.vf

def test_formatted_field():

	fmf = FormattedField( name='lower', formatter=lambda s: s.lower() )
	assert fmf.format( "TEST" ) == 'test'
	assert fmf( "TEST" ) == 'test'

def test_formatted_fields():
	ff = FormattedFields()
	ff.fields['lower'] = lambda s: s.lower()
	ff.fields['upper'] = FormattedField( name='upper', formatter=lambda s: s.upper() )

	@define
	class FormattedDataclass:

		__fmf__: FormattedFields = ff

		lower: str = field( default = 'Lower' )
		upper: str = field( default = 'Upper' )

		@property
		def fmf( self ) -> FormattedFields:
			self.__class__.__fmf__.__parent__ = self
			return self.__class__.__fmf__

	fdc = FormattedDataclass()
	FormattedDataclass.__fmf__ = ff

	assert fdc.fmf.lower == 'lower'
	assert fdc.fmf.upper == 'UPPER'

	with raises( AttributeError ):
		assert fdc.fmf.noexist == 0

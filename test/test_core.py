from dataclasses import dataclass, field

from pytest import raises

from tracs.core import FormattedField, FormattedFields, vfield, VirtualFields

def test_virtual_field():

	vf = vfield( 'one', int, default=10, display_name='One', description='Field One' )
	assert vf.name == 'one' and vf.type == int and vf.display_name == 'One' and vf.description == 'Field One'
	assert vf() == 10

	vf = VirtualField( 'two', str, value=lambda v: 'two', display_name='Two', description='Field Two' )
	assert vf.name == 'two' and vf.type == str and vf.display_name == 'Two' and vf.description == 'Field Two'
	assert vf() == 'two'

	vf = vfield( 'two', str, default=None )
	with raises( AttributeError ):
		assert vf() == 'two'

def test_virtual_fields():

	# test class enriched with virtual fields
	@dataclass
	class EnrichedDataclass:

		__vf__: VirtualFields = field( default=VirtualFields(), init=False, hash=False, compare=False )
		name: str = field( default='Name' )

		def __post_init__( self ):
			self.__vf__.__parent__ = self

		@property
		def vf( self ) -> VirtualFields:
			return self.__vf__

	EnrichedDataclass.__vf__.set_field( 'index', VirtualField( 'index', int, value=10 ) )
	EnrichedDataclass.__vf__.set_field( 'upper_name', VirtualField( 'upper_name', str, value=lambda *args: args[0].name.upper() ) )

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

	@dataclass
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

from datetime import datetime
from typing import Any, ClassVar

from attrs import define, field
from babel.numbers import format_decimal
from pytest import mark, raises

from core import is_exposed
from tracs.core import augment, derived_field_names, DerivedField, field_names, FieldFormatter, FieldFormatters, is_derived, is_internal, Metadata
from tracs.uid import UID, uid

@mark.unit
def test_derived_field():

	# setup

	def to_lower( self: Any ) -> str:
		return self.name.lower()

	def to_cap( self: Any ) -> str:
		return self.name.capitalize()

	def to_upper( self: Any ) -> str:
		return self.name.upper()

	df1 = DerivedField( name='lower_name', type=str, fn=to_lower )
	df2 = DerivedField( name='cap_name', type=str, fn=to_cap, expose=False )
	df3 = DerivedField( name='_upper_name', type=str, fn=to_upper )

	# test class enriched with derived fields
	@define
	class ClassWithDerivedFields:

		name: str = field( default='Name' )

	augment( ClassWithDerivedFields, df1 )
	augment( ClassWithDerivedFields, df2 )
	augment( ClassWithDerivedFields, df3 )

	# test

	inst = ClassWithDerivedFields()
	assert inst.name == 'Name'
	assert inst.lower_name == 'name'

	# fail to overwrite existing fields
	df = DerivedField( name='name', type=str, fn=to_lower, expose=True )
	augment( ClassWithDerivedFields, df, ignore_errors=True ) # no exception
	with raises( AttributeError ):
		augment( ClassWithDerivedFields, df, ignore_errors=False )

	# helper functions

	assert sorted( field_names( inst ) ) == ['lower_name', 'name']
	assert sorted( field_names( inst, True ) ) == ['_upper_name', 'lower_name', 'name']
	assert sorted( field_names( inst, True, True ) ) == ['_upper_name', 'cap_name', 'lower_name', 'name']
	assert sorted( field_names( inst, False, True ) ) == ['cap_name', 'lower_name', 'name']

	assert sorted( derived_field_names( inst ) ) == ['lower_name']
	assert sorted( derived_field_names( inst, True ) ) == ['_upper_name', 'lower_name']

	assert is_derived( inst, 'lower_name' )
	assert not is_derived( inst, 'name' )
	assert is_internal( inst, '_upper_name' )
	assert not is_internal( inst, 'name' )
	assert is_exposed( inst, '_upper_name' )
	assert not is_exposed( inst, 'name' )

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

	@define
	class FormattedDataclass:

		__fmf__: ClassVar[FieldFormatters] = FieldFormatters()

		name: str = field( default = 'Name' )
		age: int = field( default=10 )
		speed: float = field( default=12345.6 )
		width: float = field( default=None )

		__proxy__: Any = field( default=None, alias='__proxy__' )

		@classmethod
		def formatters( cls ) -> FieldFormatters:
			return cls.__fmf__

		def fmf( self ) -> FieldFormatters:
			if self.__proxy__ is None:
				self.__proxy__ = FieldFormatters( self.__class__.__fmf__.data, self )
			return self.__proxy__

	FormattedDataclass.__fmf__.add_all(
		FieldFormatter( name='lower', formatter=lambda v, f, l: v.lower() ),
		FieldFormatter( name='upper', formatter=lambda v, f, l: v.upper() ),
		FieldFormatter( name='speed', formatter=lambda v, f, l: format_decimal( v, f, l ), locale='en' ),
	)

	fdc = FormattedDataclass()

	assert fdc.fmf().format( 'Name', 'lower' ) == 'name'
	assert fdc.fmf().format( 10 ) == '10' # this uses the default formatter
	assert fdc.fmf().format( 12345.6, 'speed' ) == '12,345.6'

	assert fdc.fmf().format_attr( fdc, 'noexist', suppress_errors=True ) == ''
	with raises( AttributeError ):
		assert fdc.fmf().format_attr( fdc, 'noexist' ) == ''

	assert fdc.fmf().format_fields( fdc, 'name', 'age', 'speed', 'width' ) == ('Name', '10', '12,345.6', 'None')

	assert fdc.fmf().format_fields( fdc, 'name', 'age', 'speed', 'height', suppress_errors=True ) == ('Name', '10', '12,345.6', '')
	with raises( AttributeError ):
		assert fdc.fmf().format_fields( fdc, 'name', 'age', 'speed', 'height' ) == ('name', '10', '12,345.6', '')

@mark.unit
def test_metadata():

	md = Metadata(
		created=datetime( 2023, 6, 1, 10, 0, 0 ),
		modified=datetime( 2023, 7, 2, 11, 0, 0 ),
		members=[ UID( 'polar:101' ), UID( 'strava:101' ) ],
		aux={
			'custom_id': 'abcd'
		}
	)

	assert md.aux == { 'custom_id': 'abcd' }

	assert md.members == [ UID( 'polar:101' ), UID( 'strava:101' ) ]
	with raises( AttributeError ):
		assert md.custom_id == 'abcd'
	assert md['custom_id'] == 'abcd'

	assert list( md.keys() ) == ['custom_id' ]
	assert md.all_keys() == [ 'created', 'modified', 'favourite', 'member_of', 'members', 'part_of', 'parts', 'custom_id' ]

	assert list( md.values() ) == [ 'abcd' ]
	assert md.all_values() == [
		datetime( 2023, 6, 1, 10, 0 ),
		datetime( 2023, 7, 2, 11, 0 ),
		False,
		None,
		[ uid( 'polar:101' ), uid( 'strava:101' )],
		[],
		[],
		'abcd'
	]

	assert dict( md.items() ) == { 'custom_id': 'abcd' }
	assert list( md.all_items() ) == [
		('created', datetime(2023, 6, 1, 10, 0)),
		('modified', datetime(2023, 7, 2, 11, 0)),
		('favourite', False),
		('member_of', None),
		('members', [uid( 'polar:101' ), uid( 'strava:101' )]),
		('part_of', []),
		('parts', []),
		('custom_id', 'abcd')
	]

	md = Metadata()
	# todo: in the future created may not be None
	# assert md.aux.get( 'custom_id' ) is None and md.created is not None and md.modified is None
	assert md.aux.get( 'custom_id' ) is None and md.created is None and md.modified is None
	md.set( 'custom_id', 123 )
	assert md['custom_id'] == 123 and (modified := md.modified) is not None
	md.set( 'favourite', True )
	assert md.favourite == True and md.modified is not None and md.modified != modified

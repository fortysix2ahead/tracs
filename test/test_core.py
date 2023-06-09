from dataclasses import dataclass, field

from pytest import raises

from tracs.core import vfield, VirtualFields

def test_virtual_field():

	vf = vfield( 'one', int, default=10, display_name='One', description='Field One' )
	assert vf.name == 'one' and vf.type == int and vf.display_name == 'One' and vf.description == 'Field One'
	assert vf() == 10

	vf = vfield( 'two', str, default=lambda: 'two', display_name='Two', description='Field Two' )
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

	VirtualFields.__fields__ = {
		'index': vfield( 'index', int, default=10 ),
		'upper_name': vfield( 'upper_name', str, default=lambda *args: args[0].name.upper() )
	}

	edc = EnrichedDataclass()
	assert edc.name == 'Name'
	assert edc.vf.upper_name == 'NAME'
	assert edc.vf.index == 10

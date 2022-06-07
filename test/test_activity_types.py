
from gtrac.activity_types import ActivityTypes

def test_types():
	assert ActivityTypes.get( 'run' ) == ActivityTypes.run
	assert ActivityTypes.get( 'hiking' ) == ActivityTypes.hike
	assert ActivityTypes.get( 'invalid' ) == ActivityTypes.unknown
	# noinspection PyTypeChecker
	assert ActivityTypes.get( None ) == ActivityTypes.unknown

	assert ActivityTypes.get( 'run' ).display_name == 'Run'
	assert ActivityTypes.get( 'hiking' ).display_name == 'Hiking'
	assert ActivityTypes.get( 'invalid' ).display_name == 'Unknown'

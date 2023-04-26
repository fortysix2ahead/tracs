from tracs.activity_types import ActivityTypes

def test_activity_types():
	assert ActivityTypes.get( 'run' ) == ActivityTypes.run
	assert ActivityTypes.get( 'invalid' ) == ActivityTypes.unknown

	assert ActivityTypes.from_str( 'run' ) == ActivityTypes.run
	assert ActivityTypes.to_str( ActivityTypes.run ) == 'run'

	assert all( type( i ) is tuple for i in ActivityTypes.items() )
	assert all( type( i ) is str for i in ActivityTypes.names() )
	assert 'run' in ActivityTypes.names()
	assert all( type( i ) is str for i in ActivityTypes.values() )
	assert 'Run' in ActivityTypes.values()

	assert ActivityTypes.run.display_name == 'Run'

from tracs.uid import UID

def test_uid():
	uid = UID( 'polar' )
	assert uid.classifier == 'polar' and uid.local_id is None and uid.path is None
	assert uid.uid == 'polar' and uid.denotes_service()

	uid = UID( 'polar:' )
	assert uid.classifier == 'polar' and uid.local_id is None and uid.path is None
	assert uid.uid == 'polar:' and uid.denotes_service()

	uid = UID( 'polar:101' )
	assert uid.classifier == 'polar' and uid.local_id == 101 and uid.path is None
	assert uid.uid == 'polar:101' and uid.denotes_activity()

	uid = UID( 'polar:101/recording.gpx' )
	assert uid.classifier == 'polar' and uid.local_id == 101 and uid.path == 'recording.gpx'
	assert uid.uid == 'polar:101/recording.gpx' and uid.denotes_resource()

	uid = UID( 'polar:101#2' )
	assert uid.classifier == 'polar' and uid.local_id == 101 and uid.part == 2
	assert uid.uid == 'polar:101#2' and uid.denotes_part()

	# works, but does not make sense
	uid = UID( 'polar:101/recording.gpx#2' )
	assert uid.classifier == 'polar' and uid.local_id == 101 and uid.path == 'recording.gpx' and uid.part == 2
	assert uid.uid == 'polar:101/recording.gpx#2'

	assert UID( classifier='polar' ).uid == 'polar'
	assert UID( classifier='polar', local_id=101 ).uid == 'polar:101'
	assert UID( classifier='polar', local_id=101, path='recording.gpx' ).uid == 'polar:101/recording.gpx'
	assert UID( classifier='polar', local_id=101, part=1 ).uid == 'polar:101#1'
	assert UID( classifier='polar', local_id=101, path='recording.gpx', part=1 ).uid == 'polar:101/recording.gpx#1'  # works, but does not make sense ...

def test_lt():
	uid1 = UID( 'polar:101' )
	uid2 = UID( 'polar:102' )
	uid3 = UID( 'strava:101' )

	assert uid1 < uid2 < uid3
	
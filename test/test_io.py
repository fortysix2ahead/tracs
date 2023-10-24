from pytest import mark

@mark.context( config='default', lib='default', overlay='empty', takeout='waze', var='empty', persist='disk', cleanup=True )
def test_environment( fs ):
	for f in fs.walk.walk( '/' ):
		print( f )

	fs.writetext( '/test.txt', 'content' )

	for f in fs.walk.walk( '/' ):
		print( f )

@mark.context( config='default', library='default', cleanup=False )
def test_load_resource( ctx ):
	resources = ctx.db.find_resources( uid='polar:100001' )
	assert len( resources ) == 2

from pytest import mark

@mark.context( env='default', persist='disk', cleanup=True )
def test_environment( fs ):
	for f in fs.walk.walk( '/' ):
		print( f )

	fs.writetext( '/test.txt', 'content' )

	for f in fs.walk.walk( '/' ):
		print( f )

@mark.xfail # todo: do we still need this test?
@mark.context( env='default', persist='clone', cleanup=True )
def test_load_resource( env ):
	resources = env.db.find_resources( uid='polar:100001' )
	assert len( resources ) == 2

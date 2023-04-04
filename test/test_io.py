from pytest import mark

@mark.context( config='default', library='default', cleanup=False )
def test_load_resource( ctx ):
	resources = ctx.db.find_resources( uid='polar:100001' )
	assert len( resources ) == 2


from pytest import mark

from tracs.config import ApplicationContext

@mark.context( config='default', library='default', cleanup=False )
def test_reimport( ctx: ApplicationContext ):
	activities = ctx.db.activities
	print()

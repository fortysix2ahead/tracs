
from pytest import mark

from tracs.config import ApplicationContext

@mark.context( env='default', persist='clone', cleanup=True )
def test_reimport( env ):
	activities = env.db.activities

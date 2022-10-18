from pytest import mark

from tracs.config import ApplicationContext
from tracs.inout import load_resource
from tracs.inout import reimport_activities
from tracs.plugins.gpx import GPXActivity
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.polar import POLAR_FLOW_TYPE
from tracs.plugins.polar import PolarActivity


@mark.db( library='default', inmemory=True )
def test_load_resource( db ):
	resources = db.find_resources( uid='polar:100001' )
	for r in resources:
		activity = load_resource( r )
		if r.type == GPX_TYPE:
			assert type( activity ) is GPXActivity
		elif r.type == POLAR_FLOW_TYPE:
			assert type( activity ) is PolarActivity

@mark.db( library='default', inmemory=True )
def test_reimport( db ):
	ctx = ApplicationContext()
	ctx.db = db
	a = db.get( id = 3 )

	assert a.name == 'Berlin'
	reimport_activities( ctx, [a], include_recordings=False, force=True )
	assert a.name == '00:25:34;0.0 km'

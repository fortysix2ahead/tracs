from pathlib import Path
from typing import cast

from pytest import mark

from test.helpers import Mock
from tracs.db import ActivityDb
from tracs.resources import Resource
from tracs.service import Service

@mark.context( config='empty', library='empty', cleanup=False )
@mark.service( cls=Mock )
def test_fetch( service ):
	service.import_activities( skip_download=True, skip_link=True )
	db = cast( ActivityDb, service.ctx.db )
	assert len( db.resources.all() ) == 3

	p = Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.json' )
	assert p.exists() and not Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.gpx' ).exists()

	# test force flag
	mtime = p.stat().st_mtime
	service.import_activities( skip_download=True, skip_link=True )
	assert p.stat().st_mtime == mtime
	service.import_activities( force=True, skip_download=True, skip_link=True )
	assert p.stat().st_mtime > mtime

	# test pretend flag
	mtime = p.stat().st_mtime
	service.import_activities( force=True, pretend=True, skip_download=True, skip_link=True )
	assert p.stat().st_mtime == mtime

def test_filter_fetched():
	resources = [
		Resource( uid='polar:10' ),
		Resource( uid='polar:20' ),
		Resource( uid='polar:30' ),
	]

	service = Service()
	assert service.filter_fetched( resources, 'polar:20' ) == [resources[1]]
	assert service.filter_fetched( resources, 'polar:10', 'polar:20' ) == [resources[0], resources[1]]
	assert service.filter_fetched( resources, *[r.uid for r in resources] ) == resources
	assert service.filter_fetched( resources ) == resources

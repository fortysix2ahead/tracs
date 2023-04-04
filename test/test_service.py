
from pathlib import Path
from typing import cast

from pytest import mark

from test.helpers import Mock
from test.helpers import MockActivity
from tracs.db import ActivityDb
from tracs.registry import Registry
from tracs.resources import Resource
from tracs.resources import ResourceType
from tracs.service import Service

from test.helpers import MOCK_TYPE

@mark.context( config='empty', library='empty', cleanup=False )
@mark.service( cls=Mock )
def test_fetch( service ):
	db = cast( ActivityDb, service.ctx.db )
	service.import_activities( skip_download=True, skip_link=True )
	assert len( db.activities ) == 3

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

@mark.context( config='empty', library='empty', cleanup=False )
@mark.service( cls=Mock )
def test_download( service ):
	db = cast( ActivityDb, service.ctx.db )
	Registry.resource_types[MOCK_TYPE] = ResourceType( type=MOCK_TYPE, activity_cls=MockActivity ) # register mock type manually

	service.import_activities( skip_download=False, skip_link=True )

	assert len( db.resources ) == 6
	assert len( db.activities ) == 3

	p = Path( service.ctx.db_dir_for( service.name ), '1/0/0/1001/1001.gpx' )
	assert p.exists()

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

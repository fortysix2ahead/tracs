
from pathlib import Path
from pytest import mark

from tracs.inout import reimport_activities
from tracs.plugins import Registry
from tracs.plugins.handlers import JSONHandler
from tracs.plugins.polar import PolarActivity
from tracs.plugins.strava import StravaActivity

from .helpers import get_file_path

@mark.db( template='empty', inmemory=True )
def test_reimport( db ):
	json = JSONHandler().load( get_file_path( 'library/db.json' ) )
	pa = PolarActivity( data=json['_default']['1'], doc_id=1 )
	sa = StravaActivity( data=json['_default']['2'], doc_id=2 )

	Registry.services['polar'].base_path = Path( get_file_path( 'library/db.json' ).parent, 'polar' )
	Registry.services['strava'].base_path = Path( get_file_path( 'library/db.json' ).parent, 'strava' )

	assert pa.name == 'Berlin'
	pa.name = 'Hamburg'
	reimport_activities( None, [pa], db, from_raw=True, force=True )
	assert pa.name == 'Berlin'

	assert sa.name == 'Berlin'
	reimport_activities( None, [sa], db, from_raw=True, force=True )
	assert sa.name == 'Munich'

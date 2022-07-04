
from pathlib import Path
from pytest import mark

from tracs.inout import reimport_activities
from tracs.plugins import Registry
from tracs.plugins.handlers import JSONHandler
from tracs.plugins.polar import PolarActivity

from .helpers import get_file_path

@mark.db( template='empty', inmemory=True )
def test_reimport( db ):
	json = JSONHandler().load( get_file_path( 'library/db.json' ) )
	pa = PolarActivity( data=json['_default']['1'], doc_id=1 )

	base_path = Path( get_file_path( 'library/db.json' ).parent, 'polar' )
	# noinspection PyUnresolvedReferences
	Registry.services['polar']._base_path = base_path

	assert pa.name == 'Berlin'
	pa.name = 'Hamburg'
	reimport_activities( None, [pa], db, from_raw=True, force=True )
	assert pa.name == 'Berlin'

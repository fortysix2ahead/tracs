
from datetime import datetime, timedelta, timezone

from dateutil.tz import tzlocal, tzoffset
from pytest import mark

from tracs.activity_types import ActivityTypes
from tracs.plugins.polar import Polar, PolarFlowImporter
from tracs.plugins.polar.io import polar_model_converter, PolarTrainingSessionImporter
from tracs.plugins.polar.models.account_profile import AccountProfile
from tracs.plugins.polar.models.training_session import TrainingSession

importer = PolarTrainingSessionImporter()

@mark.file( 'environments/takeouts/takeouts/polar/account-profile-59284768-38e86c0f-8593-48b0-82a7-4d39e926483b.json' )
def test_account_profile( fs_path ):
	fs, path = fs_path
	model: AccountProfile = polar_model_converter.loads( fs.readbytes( path ), AccountProfile )
	assert model.exportVersion == '2.6'

@mark.file( 'environments/takeouts/takeouts/polar/training-session-2022-10-16T14:23:39-7505780534-25099b60-224b-4e6b-8f47-fb00f6d2df75.json' )
def test_training_session( fs_path ):
	model: TrainingSession = polar_model_converter.loads( fs_path[0].readbytes( fs_path[1] ), TrainingSession )
	assert model.application.name == 'Polar Flow'

@mark.file( 'environments/takeouts/takeouts/polar/training-session-2022-10-16T14:23:39-7505780534-25099b60-224b-4e6b-8f47-fb00f6d2df75.json' )
def test_exercise( fs_path ):
	fs, path = fs_path
	pa = importer.load_as_activity( fs=fs, path=path, attach=False )[0]
	# assert pa.type == ActivityTypes.run
	assert pa.starttime == datetime( 2022, 10, 16, 12, 23, 39, tzinfo=timezone.utc )
	assert pa.starttime_local == datetime( 2022, 10, 16, 14, 23, 39, tzinfo=tzoffset(None, 7200) )
	assert pa.duration == timedelta( seconds=11582, microseconds=216000 )

@mark.context( env='default', cleanup=False )
@mark.service( cls=Polar, init=True, register=True )
def test_takeout_import( service ):
	src_fs = service.ctx.takeout_fs( 'polar' )
	activities = service.import_activities( src_fs=src_fs, src_path=None, force=True )
	assert [ a.uid for a in activities ] == [
		'polar:7537918035', 'polar:7563345425', 'polar:7563345432', 'polar:7563345422'
	]

@mark.context( env='takeouts', cleanup=False )
@mark.service( cls=Polar, init=True, register=True )
def test_takeout_import( service ):
	src_fs = service.ctx.takeout_fs( 'polar' )
	activities = service.import_activities( src_fs=src_fs, src_path=None, force=True )
	assert [ a.uid for a in activities ] == [
		'polar:7505780534', 'polar:7537918051', 'polar:7537918035', 'polar:7563345425', 'polar:7563345432', 'polar:7563345422'
	]

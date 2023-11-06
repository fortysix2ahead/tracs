from pathlib import Path
from platform import system

import platformdirs
from fs.base import FS
from fs.multifs import MultiFS
from fs.osfs import OSFS

from pytest import mark

from tracs.application import Application
from tracs.config import ApplicationContext, APPNAME
from tracs.registry import Registry

from test.conftest import PERSISTANCE_NAME

@mark.context( env='empty', persist='clone', cleanup=True )
def test_context( fs: MultiFS ):
	vrfs = fs.get_fs( PERSISTANCE_NAME )
	vrp = vrfs.getsyspath( '' )

	ctx = ApplicationContext()
	assert ctx.config_fs
	assert ctx.config_dir == OSFS( root_path=platformdirs.user_config_dir( 'tracs' ), expand_vars=True ).getsyspath( '' )
	assert ctx.lib_dir == OSFS( root_path=platformdirs.user_config_dir( 'tracs' ), expand_vars=True ).getsyspath( '' )
	assert ctx.db_dir == OSFS( root_path=platformdirs.user_config_dir( 'tracs' ), expand_vars=True ).getsyspath( 'db/' )

	ctx = ApplicationContext( config_dir=vrp )
	assert ctx.config_fs
	assert ctx.config_dir == vrp
	assert ctx.config_file == vrfs.getsyspath( '/config.yaml' )
	assert ctx.state_file == vrfs.getsyspath( '/state.yaml' )
	assert ctx.lib_dir == vrp
	assert ctx.db_dir == f'{vrp}db/'
	assert ctx.overlay_dir == f'{vrp}overlay/'
	assert ctx.plugin_dir( 'polar' ) == f'{vrp}db/polar/'

	assert ctx.takeouts_dir == f'{vrp}takeouts/'
	assert ctx.takeout_dir( 'polar' ) == f'{vrp}takeouts/polar/'

	ctx = ApplicationContext( config_file=f'{vrp}/config.yaml' )
	assert ctx.config_fs
	assert ctx.config_dir == vrp
	assert ctx.config_file == vrfs.getsyspath( '/config.yaml' )
	assert ctx.lib_dir == vrp
	assert ctx.db_dir == f'{vrp}db/'

def test_app_constructor():
	app =  Application.__new__( Application, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming', APPNAME )
	elif system() == 'Linux':
		cfg_dir = Path( home, '.config', APPNAME )
	elif system() == 'Darwin':
		cfg_dir = Path( home, 'Library', 'Application Support', APPNAME )
	else:
		return

	assert app.ctx.config_dir == f'{str( cfg_dir )}/'
	assert app.ctx.lib_dir == f'{str( cfg_dir )}/'

@mark.context( env='empty', persist='clone', cleanup=True )
def test_app_constructor_cfg_dir( ctx ):
	cfg_dir = ctx.config_dir
	cfg = f'{cfg_dir}/config.yaml'
	app =  Application.__new__( Application, config_file=cfg, verbose=False, debug=False, force=False )

	assert app.ctx.config_dir == f'{str( cfg_dir )}'
	assert app.ctx.lib_dir == f'{str( cfg_dir )}'

@mark.context( env='empty', persist='clone', cleanup=True )
def test_app_constructor_lib_dir( ctx ):
	lib_dir = ctx.lib_dir
	app =  Application.__new__( Application, lib_dir=lib_dir, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming', APPNAME )
	elif system() == 'Linux':
		cfg_dir = Path( home, '.config', APPNAME )
	elif system() == 'Darwin':
		cfg_dir = Path( home, 'Library', 'Application Support', APPNAME )
	else:
		return

	assert app.ctx.config_dir == f'{str( cfg_dir )}/'
	assert app.ctx.lib_dir == f'{str( ctx.lib_dir )}'

def test_default_environment():
	app = Application.__new__( Application, verbose=False, debug=False, force=False ) # matches default object creation
	assert app.ctx.debug == False
	assert app.ctx.verbose == False
	assert app.ctx.force == False

	# assert Registry.instance().service_names() == [ 'bikecitizens', 'local', 'polar', 'strava', 'stravaweb', 'waze' ]

@mark.context( env='debug', persist='clone', cleanup=True )
def test_debug_environment( ctx ):
	app = Application.__new__( Application, config_file=f'{ctx.config_dir}/config.yaml', verbose=None, debug=None, force=None )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == False

@mark.context( env='debug', persist='clone', cleanup=True )
def test_parameterized_environment( ctx ):
	# override configuration loaded from file to simulate command line parameters
	cfg_file = f'{ctx.config_dir}/config.yaml'
	app = Application.__new__( Application, config_file=cfg_file, verbose=None, debug=None, force=True )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == True

@mark.skip
@mark.context( env='local', persist='clone', cleanup=True )
def test_disabled_environment( ctx ):
	cfg_file = f'{ctx.config_dir}/config.yaml'
	Application.__new__( Application, configuration=cfg_file )
	assert Registry.instance().service_names() == [ 'local' ]

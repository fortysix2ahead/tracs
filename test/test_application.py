
from pathlib import Path
from platform import system

from pytest import mark

from tracs.application import Application
from tracs.config import APPNAME
from tracs.config import CONFIG_FILENAME
from tracs.config import DB_DIRNAME
from tracs.config import OVERLAY_DIRNAME
from tracs.config import STATE_FILENAME
from tracs.config import ApplicationConfig as cfg
from tracs.config import ApplicationContext
from tracs.config import VAR_DIRNAME
from .helpers import get_config_path

def test_app_constructor():
	app =  Application.__new__( Application, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False )
	ctx = app.ctx
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming' )
	elif system() == 'Linux' or system() == 'Darwin':
		cfg_dir = Path( home, '.config' )
	else:
		return

	assert ctx.cfg_dir == Path( cfg_dir, APPNAME )
	assert ctx.cfg_file == Path( cfg_dir, APPNAME, CONFIG_FILENAME )
	assert ctx.state_file == Path( cfg_dir, APPNAME, STATE_FILENAME )

	assert ctx.lib_dir == Path( cfg_dir, APPNAME )
	assert ctx.db_dir == Path( cfg_dir, APPNAME, DB_DIRNAME )

	assert ctx.overlay_dir == Path( ctx.db_dir, OVERLAY_DIRNAME )
	assert ctx.var_dir == Path( ctx.db_dir, VAR_DIRNAME )

@mark.context( config='empty' )
def test_app_constructor_cfg_dir( ctx ):
	cfg_dir = ctx.cfg_dir
	app =  Application.__new__( Application, config_dir=cfg_dir, lib_dir=None, verbose=False, debug=False, force=False )

	assert app.ctx.cfg_dir == cfg_dir
	assert app.ctx.cfg_file == Path( cfg_dir, 'config.yaml' )
	assert app.ctx.state_file == Path( cfg_dir, 'state.yaml' )

	assert app.ctx.lib_dir == Path( cfg_dir )
	assert app.ctx.db_dir == Path( cfg_dir, 'db' )

def test_app_constructor_lib_dir():
	env_path = get_config_path( 'debug', False )
	ctx = ApplicationContext()
	app =  Application.__new__( Application, ctx=ctx, config_dir=None, lib_dir=env_path, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		system_cfg_dir = Path( home, 'Appdata/Roaming' )
	elif system() == 'Linux' or system() == 'Darwin':
		system_cfg_dir = Path( home, '.config' )
	else:
		return

	assert app.cfg_dir == Path( system_cfg_dir, 'tracs' )
	assert app.cfg_file == Path( system_cfg_dir, 'tracs/config.yaml' )
	assert app.state_file == Path( system_cfg_dir, 'tracs/state.yaml' )

	assert app.lib_dir == Path( env_path )
	assert app.db_dir == Path( env_path, 'db' )
	assert app.db_file == Path( env_path, 'db/db.json' )

	assert app.backup_dir == Path( env_path, 'db/.backup' )

def test_environment():
	# load default/debug configuration
	ctx = ApplicationContext()
	Application._instance = Application.__new__( Application, ctx=ctx, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False ) # matches default object creation
	assert cfg['debug'].get() == False
	assert cfg['verbose'].get() == False
	assert cfg['force'].get() == False

	cfg_dir = get_config_path( 'debug', False )

	Application._instance = Application.__new__( Application, ctx=ctx, config_dir=cfg_dir, lib_dir=None, verbose=None, debug=None, force=None ) # matches default object creation
	assert cfg['debug'].get() == True
	assert cfg['verbose'].get() == True
	assert cfg['force'].get() == False

	# override configuration loaded from file to simulate command line parameters
	Application._instance = Application.__new__( Application, ctx=ctx, config_dir=cfg_dir, lib_dir=None, verbose=None, debug=None, force=True ) # matches default object creation
	assert cfg['debug'].get() == True
	assert cfg['verbose'].get() == True
	assert cfg['force'].get() == True

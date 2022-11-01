
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

@mark.context( library='empty' )
def test_app_constructor_lib_dir( ctx ):
	lib_dir = ctx.lib_dir
	app =  Application.__new__( Application, lib_dir=lib_dir, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming' )
	elif system() == 'Linux' or system() == 'Darwin':
		cfg_dir = Path( home, '.config' )
	else:
		return

	assert app.ctx.cfg_dir == Path( cfg_dir, APPNAME )
	assert app.ctx.lib_dir == ctx.lib_dir

def test_default_environment():
	app = Application.__new__( Application, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False ) # matches default object creation
	assert app.ctx.debug == False
	assert app.ctx.verbose == False
	assert app.ctx.force == False

@mark.context( config='debug' )
def test_debug_environment( ctx ):
	app = Application.__new__( Application, config_dir=ctx.cfg_dir, verbose=None, debug=None, force=None )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == False

@mark.context( config='debug' )
def test_parameterized_environment( ctx ):
	# override configuration loaded from file to simulate command line parameters
	app = Application.__new__( Application, config_dir=ctx.cfg_dir, verbose=None, debug=None, force=True )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == True

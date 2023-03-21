
from pathlib import Path
from platform import system

from pytest import mark

from tracs.application import Application
from tracs.config import APPNAME

def test_app_constructor():
	app =  Application.__new__( Application, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False )
	ctx = app.ctx
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming', APPNAME )
	elif system() == 'Linux':
		cfg_dir = Path( home, '.config', APPNAME )
	elif system() == 'Darwin':
		cfg_dir = Path( home, 'Library', 'Application Support', APPNAME )
	else:
		return

	assert ctx.config_dir == str( Path( cfg_dir ) )
	assert ctx.lib_dir == str( Path( cfg_dir ) )

@mark.context( config='empty', library='empty' )
def test_app_constructor_cfg_dir( ctx ):
	cfg_dir = ctx.config_dir
	app =  Application.__new__( Application, config_dir=cfg_dir, lib_dir=None, verbose=False, debug=False, force=False )

	assert app.ctx.config_dir == str( cfg_dir )
	assert app.ctx.lib_dir == str( Path( cfg_dir ) )

@mark.context( config='empty', library='empty' )
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

	assert app.ctx.config_dir == str( Path( cfg_dir ) )
	assert app.ctx.lib_dir == str( ctx.lib_dir )

def test_default_environment():
	app = Application.__new__( Application, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False ) # matches default object creation
	assert app.ctx.debug == False
	assert app.ctx.verbose == False
	assert app.ctx.force == False

@mark.context( config='debug', library='empty' )
def test_debug_environment( ctx ):
	app = Application.__new__( Application, config_dir=ctx.config_dir, verbose=None, debug=None, force=None )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == False

@mark.context( config='debug', library='empty' )
def test_parameterized_environment( ctx ):
	# override configuration loaded from file to simulate command line parameters
	app = Application.__new__( Application, config_dir=ctx.config_dir, verbose=None, debug=None, force=True )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == True


from pathlib import Path
from platform import system

from confuse import ConfigSource, Configuration
from pytest import mark

from tracs.application import Application
from tracs.config import APPNAME
from tracs.registry import Registry

def test_context():
	cfg = Configuration( 'tracs', 'tracs' )
	cfg.set_env()
	cfg.set_args( {'debug': 'arg'} )
	cfg.set( ConfigSource.of( { 'debug': 10 } ) )

	print( cfg['debug'].get() )
	print( cfg['debug'].as_number() )

def test_app_constructor():
	app =  Application.__new__( Application, configuration=None, library=None, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming', APPNAME )
	elif system() == 'Linux':
		cfg_dir = Path( home, '.config', APPNAME )
	elif system() == 'Darwin':
		cfg_dir = Path( home, 'Library', 'Application Support', APPNAME )
	else:
		return

	assert app.ctx.config_dir == str( cfg_dir )
	assert app.ctx.lib_dir == str( cfg_dir )

@mark.context( config='empty', library='empty' )
def test_app_constructor_cfg_dir( ctx ):
	cfg_dir = ctx.config_dir
	cfg = f'{cfg_dir}/config.yaml'
	app =  Application.__new__( Application, configuration=cfg, library=None, verbose=False, debug=False, force=False )

	assert app.ctx.config_dir == str( cfg_dir )
	assert app.ctx.lib_dir == str( Path( cfg_dir ) )

@mark.context( config='empty', library='empty' )
def test_app_constructor_lib_dir( ctx ):
	lib_dir = ctx.lib_dir
	app =  Application.__new__( Application, library=lib_dir, verbose=False, debug=False, force=False )
	home = Path.home()

	if system() == 'Windows':
		cfg_dir = Path( home, 'Appdata/Roaming', APPNAME )
	elif system() == 'Linux':
		cfg_dir = Path( home, '.config', APPNAME )
	elif system() == 'Darwin':
		cfg_dir = Path( home, 'Library', 'Application Support', APPNAME )
	else:
		return

	assert app.ctx.config_dir == str( cfg_dir )
	assert app.ctx.lib_dir == str( ctx.lib_dir )

def test_default_environment():
	app = Application.__new__( Application, configuration=None, library=None, verbose=False, debug=False, force=False ) # matches default object creation
	assert app.ctx.debug == False
	assert app.ctx.verbose == False
	assert app.ctx.force == False

	assert Registry.instance().service_names() == [ 'bikecitizens', 'local', 'polar', 'strava', 'waze' ]

@mark.context( config='debug', library='empty' )
def test_debug_environment( ctx ):
	cfg_file = f'{ctx.config_dir}/config.yaml'
	app = Application.__new__( Application, configuration=cfg_file, verbose=None, debug=None, force=None )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == False

@mark.context( config='debug', library='empty' )
def test_parameterized_environment( ctx ):
	# override configuration loaded from file to simulate command line parameters
	cfg_file = f'{ctx.config_dir}/config.yaml'
	app = Application.__new__( Application, configuration=cfg_file, verbose=None, debug=None, force=True )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == True

@mark.context( config='local_only', library='empty' )
def test_disabled_environment( ctx ):
	cfg_file = f'{ctx.config_dir}/config.yaml'
	Application.__new__( Application, configuration=cfg_file )
	assert Registry.instance().service_names() == [ 'local' ]

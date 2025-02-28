from pathlib import Path
from platform import system

from fs.appfs import UserDataFS
from pytest import mark

from tracs.application import Application
from tracs.constants import APPNAME
from tracs.context import current_ctx

def test_app_constructor():
	app =  Application.__new__( Application, verbose=False, debug=False, force=False, json=False )
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
	app =  Application.__new__( Application, configuration=cfg, verbose=False, debug=False, force=False )

	assert app.ctx.config_dir == f'{str( cfg_dir )}'
	assert app.ctx.lib_dir == UserDataFS( 'tracs', create=True ).getsyspath( '' )

@mark.context( env='empty', persist='clone', cleanup=True )
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

	assert app.ctx.config_dir == f'{str( cfg_dir )}/'
	assert app.ctx.lib_dir == f'{str( ctx.lib_dir )}'


def test_default_environment():
	app = Application.__new__( Application, verbose=False, debug=False, force=False ) # matches default object creation
	assert app.ctx.debug == False
	assert app.ctx.verbose == False
	assert app.ctx.force == False

@mark.context( env='debug', persist='clone', cleanup=True )
def test_debug_environment( ctx ):
	app = Application.__new__( Application, configuration=f'{ctx.config_dir}/config.yaml', verbose=None, debug=None, force=None )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == False

@mark.context( env='debug', persist='clone', cleanup=True )
def test_parameterized_environment( ctx ):
	# override configuration loaded from file to simulate command line parameters
	cfg_file = f'{ctx.config_dir}/config.yaml'
	app = Application.__new__( Application, configuration=cfg_file, verbose=None, debug=None, force=True )
	assert app.ctx.debug == True
	assert app.ctx.verbose == True
	assert app.ctx.force == True

@mark.skip
@mark.context( env='local', persist='clone', cleanup=True )
def test_disabled_environment( ctx ):
	cfg_file = f'{ctx.config_dir}/config.yaml'
	Application.__new__( Application, configuration=cfg_file )
	# noinspection PyTestUnpassedFixture
	assert current_ctx().registry.service_names() == [ 'local' ]

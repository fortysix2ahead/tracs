from pathlib import Path
from platform import system

from tracs.application import Application
from tracs.config import ApplicationConfig as cfg
from .helpers import get_config_path

from .helpers import get_env
from .helpers import get_db

def test_app_constructor():
	app =  Application.__new__( Application, db=None, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False )
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

	assert app.lib_dir == Path( system_cfg_dir, 'tracs' )
	assert app.db_dir == Path( system_cfg_dir, 'tracs/db' )
	assert app.db_file == Path( system_cfg_dir, 'tracs/db/db.json' )

	assert app.backup_dir == Path( system_cfg_dir, 'tracs/db/.backup' )

def test_app_constructor_cfg_dir():
	env_path = get_config_path( 'debug', False )
	app =  Application.__new__( Application, db=None, config_dir=env_path, lib_dir=None, verbose=False, debug=False, force=False )

	assert app.cfg_dir == Path( env_path )
	assert app.cfg_file == Path( env_path, 'config.yaml' )
	assert app.state_file == Path( env_path, 'state.yaml' )

	assert app.lib_dir == Path( env_path )
	assert app.db_dir == Path( env_path, 'db' )
	assert app.db_file == Path( env_path, 'db/db.json' )

	assert app.backup_dir == Path( env_path, 'db/.backup' )

def test_app_constructor_lib_dir():
	env_path = get_config_path( 'debug', False )
	app =  Application.__new__( Application, db=None, config_dir=None, lib_dir=env_path, verbose=False, debug=False, force=False )
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
	Application._instance = Application.__new__( Application, db=None, config_dir=None, lib_dir=None, verbose=False, debug=False, force=False ) # matches default object creation
	assert cfg['debug'].get() == False
	assert cfg['verbose'].get() == False
	assert cfg['force'].get() == False

	cfg_dir = get_config_path( 'debug', False )

	Application._instance = Application.__new__( Application, db=None, config_dir=cfg_dir, lib_dir=None, verbose=None, debug=None, force=None ) # matches default object creation
	assert cfg['debug'].get() == True
	assert cfg['verbose'].get() == True
	assert cfg['force'].get() == False

	# override configuration loaded from file to simulate command line parameters
	Application._instance = Application.__new__( Application, db=None, config_dir=cfg_dir, lib_dir=None, verbose=None, debug=None, force=True ) # matches default object creation
	assert cfg['debug'].get() == True
	assert cfg['verbose'].get() == True
	assert cfg['force'].get() == True

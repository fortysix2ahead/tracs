from importlib.resources import path
from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Tuple

from pytest import fixture
from yaml import SafeLoader
from yaml import load as load_yaml

from tracs.config import ApplicationConfig as cfg
from tracs.config import ApplicationState as state
from tracs.config import CLASSIFIER
from tracs.registry import Registry
from .helpers import var_run_path

@fixture
def var_config_path( request ) -> Optional[Path]:
	marker = request.node.get_closest_marker( 'config_file' )
	if marker:
		with path( 'test', '__init__.py' ) as test_pkg_path:
			config_path = Path( test_pkg_path.parent.parent, 'var', marker.args[0] )
			return config_path if config_path.exists() else None
	else:
		return None

@fixture
def var_config( request ) -> bool:
	marker = request.node.get_closest_marker( 'config_file' )
	if marker:
		with path( 'test', '__init__.py' ) as test_pkg_path:
			config_path = Path( test_pkg_path.parent.parent, 'var', marker.args[0] )
			if config_path.exists():
				cfg.set_file( config_path )
				return True

	return False

@fixture
def config_state( request ) -> Optional[Tuple[Dict, Dict]]:
	config_dict, state_dict = None, None
	config_marker = request.node.get_closest_marker( 'config_file' )
	state_marker = request.node.get_closest_marker( 'state_file' )
	if config_marker and state_marker:
		with path( 'test', '__init__.py' ) as test_pkg_path:
			config_path = Path( test_pkg_path.parent.parent, 'var', config_marker.args[0] )
			config = None
			if config_path.exists():
				cfg.set_file( config_path )
				config_dict = load_yaml( config_path.read_bytes(), SafeLoader )

			state_path = Path( test_pkg_path.parent.parent, 'var', state_marker.args[0] )
			if state_path.exists():
				state.set_file( state_path )
				state_dict = load_yaml( state_path.read_bytes(), SafeLoader )

	return config_dict, state_dict

@fixture
def var_dir() -> Path:
	return var_run_path()

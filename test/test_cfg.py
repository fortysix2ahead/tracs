
from importlib import import_module
from importlib.resources import path as pkg_path

from confuse import Configuration

def test_cfg_default():
	config = Configuration( f'gtrac', __name__, read=False )

	# load defaults from internal package
	with pkg_path( import_module( f'gtrac.config' ), 'config.yaml' ) as p:
		config.set_file( p )

	assert config['db']['cache_size'].get() == 100

	# load custom config
	with pkg_path( import_module( f'test.configurations.default' ), 'config.yaml' ) as p:
		config.set_file( p )

	assert config['db']['cache_size'].get() == 0

	config['db']['cache_size'] = 20

	assert config['db']['cache_size'].get() == 20

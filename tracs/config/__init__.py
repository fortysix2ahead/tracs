
from __future__ import annotations

from importlib import import_module
from importlib.resources import path as pkg_path
from pathlib import Path
from typing import Tuple

from confuse import Configuration
from confuse import Subview
from rich.console import Console

APPNAME = 'tracs'

BACKUP_DIRNAME = '.backup'
CACHE_DIRNAME = 'cache'
DB_DIRNAME = 'db'
DB_FILENAME = 'db.json'
LOG_DIRNAME = 'logs'
LOG_FILENAME = f'{APPNAME}.log'

CONFIG_FILENAME = 'config.yaml'
STATE_FILENAME = 'state.yaml'

TABLE_NAME_DEFAULT = '_default'
TABLE_NAME_ACTIVITIES = 'activities'

CLASSIFIER = 'classifier'
CLASSIFIERS = 'classifiers'

KEY_CLASSIFER = '_classifier'
KEY_GROUPS = '_groups'
KEY_METADATA = '_metadata'
KEY_PARTS = '_parts'
KEY_PLUGINS = 'plugins'
KEY_SERVICE = KEY_CLASSIFER
KEY_RAW = '_raw'
KEY_RESOURCES = '_resources'
KEY_VERSION = 'version'

NAMESPACE_BASE = APPNAME
NAMESPACE_CONFIG = f'{NAMESPACE_BASE}.config'
NAMESPACE_PLUGINS = f'{NAMESPACE_BASE}.plugins'
NAMESPACE_SERVICES = f'{NAMESPACE_BASE}.services'

ApplicationConfig = Configuration( APPNAME, __name__, read=False )
ApplicationState = Configuration( f'{APPNAME}-state', __name__, read=False )

APP_CFG = ApplicationConfig
APP_STATE = ApplicationState

console = Console()

# load defaults from internal package
with pkg_path( import_module( NAMESPACE_CONFIG ), CONFIG_FILENAME ) as p:
	ApplicationConfig.set_file( p )
with pkg_path( import_module( NAMESPACE_CONFIG ), STATE_FILENAME ) as p:
	ApplicationState.set_file( p )

def plugin_config_state( plugin: str ) -> Tuple[Subview, Subview]:
	return ApplicationConfig[KEY_PLUGINS][plugin], ApplicationState[KEY_PLUGINS][plugin]

class GlobalConfig:

	app = None
	db = None
	cfg: Configuration = APP_CFG
	state: Configuration = APP_STATE

	cfg_dir: Path = None
	db_dir: Path = None
	db_file: Path = None
	lib_dir: Path = None

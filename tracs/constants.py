
from importlib.resources import path as pkg_path

# version

__version__ = '0.2.0-dev'

# general constants

APPNAME = 'tracs'
APP_PKG_NAME = 'tracs'
PLUGINS_PKG_NAME = 'plugins'
PLUGINS_PKG = f'{APP_PKG_NAME}.{PLUGINS_PKG_NAME}'

# plugin modules / namespaces

PLUGIN_PATH = '/tracs/plugins'
NS_BASE = APPNAME
NS_CONFIG = f'{NS_BASE}.config'
NS_SERVICES = f'{NS_BASE}.services'

# system paths

with pkg_path( APP_PKG_NAME, '__init__.py' ) as path:
	INSTALL_PATH = str( path.parent )

with pkg_path( PLUGINS_PKG, '__init__.py' ) as path:
	PLUGINS_PATH = str( path.parent )

# directory/file names

BACKUP_DIRNAME = 'backup'
CACHE_DIRNAME = 'cache'
DB_DIRNAME = 'db'
DB_FILENAME = 'db.json'
IMPORT_DIRNAME = 'imports'
LOG_DIRNAME = 'logs'
LOG_FILENAME = f'{APPNAME}.log'
OVERLAY_DIRNAME = 'overlay'
RESOURCES_DIRNAME = 'resources'
TAKEOUT_DIRNAME = 'takeouts'
TMP_DIRNAME = 'tmp'
VAR_DIRNAME = 'var'

# configuration filenames

CONFIG_FILENAME = 'config.yaml'
STATE_FILENAME = 'state.yaml'
DEFAULT_CONFIG_FILENAME = 'defaults/config.yaml'
DEFAULT_STATE_FILENAME = 'defaults/state.yaml'

# global keyword arguments

GLOBAL_KWARGS = [ 'debug', 'force', 'verbose', 'json', 'pretend' ]

# misc keys

CLASSIFIER = 'classifier'
CLASSIFIERS = 'classifiers'

KEY_CONFIGURATION = 'configuration'
KEY_CLASSIFER = 'classifier'
KEY_GROUP = 'group'
KEY_GROUPS = 'groups'
KEY_LAST_DOWNLOAD = 'last_download'
KEY_LAST_FETCH = 'last_fetch'
KEY_METADATA = 'metadata'
KEY_PARTS = 'parts'
KEY_PLUGINS = 'plugins'
KEY_SERVICE = KEY_CLASSIFER
KEY_RAW = 'raw'
KEY_RESOURCES = 'resources'
KEY_VERSION = 'version'

# configuration keys

CFG_BASE_URL = '_base_url'
CFG_DB_FS = '_db_fs'
CFG_FS = '_fs'
CFG_PATH = 'path'
CFG_TMP_FS = '_tmp_fs'
CFG_USER_ID = 'user_id'

from logging import getLogger
from typing import Dict
from uuid import NAMESPACE_URL, uuid5

from attrs import define, field
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.orjson import make_converter
from fs.base import FS
from fs.osfs import OSFS
from orjson import dumps, loads, OPT_APPEND_NEWLINE, OPT_INDENT_2, OPT_SORT_KEYS

from tracs.resources import Resource, Resources

log = getLogger( __name__ )

ORJSON_OPTIONS = OPT_APPEND_NEWLINE | OPT_INDENT_2 | OPT_SORT_KEYS

RESOURCES_NAME = 'resources.json'
RESOURCES_PATH = f'/{RESOURCES_NAME}'
SCHEMA_NAME = 'schema.json'
SCHEMA_PATH = f'/{SCHEMA_NAME}'

RESOURCE_CONVERTER = make_converter()
SCHEMA_CONVERTER = make_converter()

# converter configuration

hook = make_dict_unstructure_fn( Resource, RESOURCE_CONVERTER, _cattrs_omit_if_default=True, )
RESOURCE_CONVERTER.register_unstructure_hook( Resources, hook )

# resource handling

def load_resources( fs: FS ) -> Resources:
	resources = RESOURCE_CONVERTER.loads( fs.readbytes( RESOURCES_PATH ), Dict[str, Resource] )
	log.debug( f'loaded {len( resources )} resource entries from {RESOURCES_NAME}' )
	return Resources( data = resources )

# schema handling

@define
class Schema:

	version: int = field( default=None )

def load_schema( fs: FS ) -> Schema:
	schema = SCHEMA_CONVERTER.loads( fs.readbytes( SCHEMA_PATH ), Schema )
	log.debug( f'loaded database schema from {SCHEMA_PATH}, schema version = {schema.version}' )
	return schema

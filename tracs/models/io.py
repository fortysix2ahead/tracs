from typing import Tuple

from cattrs.preconf.orjson import OrjsonConverter

def to_floatstr( v, t ):
	return v if isinstance( v, float ) else float( v )

def make_polar_converter() -> OrjsonConverter:
	c = OrjsonConverter( omit_if_default=True, detailed_validation=True )

	# c.register_unstructure_hook( float|str, lambda v: str( v ) if isinstance( v, float ) else v )

	c.register_structure_hook( float|str, to_floatstr )

	return c

polar_model_converter = make_polar_converter()


from __future__ import annotations

# from inspect import getfullargspec
from logging import getLogger

from ..registry import load

log = getLogger( __name__ )

# internal helpers

# decorators

# decorator for service classes

# experimental decorators

# A decorator with arguments is defined as a function that returns a standard decorator.
# A standard decorator is defined as function that returns a function.

# def handler( *args, **kwargs ):
# 	def handler_class( cls ):
# 		if isclass( cls ):
# 			instance = cast( Handler, cls() )
# 			for t in instance.types():
# 				Registry.register_handler( instance, t )
# 			return cls
# 		else:
# 			raise RuntimeError( 'only classes can be decorated with the @handler decorator' )
#
# 	if len( args ) == 0 and 'types' in kwargs:
# 		return handler_class
# 	elif len( args ) == 1:
# 		handler_class( args[0] )

# setup

# trigger auto load

load()

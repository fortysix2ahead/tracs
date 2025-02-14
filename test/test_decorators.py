# sample code for generic decorating:
from inspect import currentframe, FrameInfo, isclass, isfunction, getframeinfo, getouterframes, stack
from typing import Any, Callable, Dict, List, Optional, Tuple

from attrs import define, field

DECORATIONS = list()

def _decorator_with_args_and_kwargs( *args, **kwargs ):

	def inner( fncls = None ):

		#def wrapper( *wrapper_args, **wrapper_kwargs ):
		#	print( 'wrapper' )
		#	fncls( *wrapper_args, **wrapper_kwargs )

		print( fncls, args, kwargs )

		if fncls is not None:
			DECORATIONS.append( (fncls, args, kwargs) )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		DECORATIONS.append( (args[0], (), {} ) )
		if isclass( args[0] ):
			return args[0]

	return inner

def real_decorator( *args, **kwargs ):
	return _decorator_with_args_and_kwargs( *args, **kwargs )

@real_decorator
def f1():
	return 1

@real_decorator( 'some value', 'some other value' )
def f2():
	return 2

@real_decorator( kwarg_one='some value', kwarg_two='some other value' )
def f3():
	return 3

@real_decorator( 'some value', 'some other value', kwarg_one='some value', kwarg_two='some other value' )
def f4():
	return 4

@real_decorator
class C1:
	def __init__( self ):
		self.value = 'c1'

@real_decorator( 'some value', 'some other value' )
class C2:
	pass

@real_decorator( kwarg_one='some value', kwarg_two='some other value' )
class C3:
	pass

@real_decorator( 'some value', 'some other value', kwarg_one='some value', kwarg_two='some other value' )
class C4:
	pass

def test_decorators():
	decorations = DECORATIONS
	assert len( decorations ) == 8

	assert isfunction( f1 )
	assert f1() == 1
	assert f2() == 2
	assert f3() == 3
	assert f4() == 4

	c1 = C1()
	assert c1.value == 'c1'
	assert isclass( C1 )
	assert isinstance( c1, C1 )

# taken from plugin manager

@define
class Decorator:

	fncls: Any = field( default=None )
	args: Tuple = field( factory=tuple )
	kwargs: Dict = field( factory=dict )
	frame = field( default=None )

	@property
	def caller_name( self ) -> str|None:
		return self.frame.f_code.co_name if self.frame else None

@define
class DecoratorRegistry:

	decorators: List = field( factory=list )
	call_counter: int = field( default=0 )

	def add( self, fncls: Any, args: Tuple, kwargs: Dict, frame: FrameInfo = None ):
		self.decorators.append( Decorator( fncls, args, kwargs, frame ) )

REGISTRY = DecoratorRegistry()

def _register( *args, **kwargs ) -> Callable:
	_current_frame = kwargs.pop( '_current_frame', None )

	def _inner( fncls ):
		if fncls is not None:
			REGISTRY.add( fncls, args, kwargs, _current_frame )
			return fncls
		else:
			return args[0]()

	if args and not kwargs and callable( args[0] ):
		REGISTRY.add( args[0], (), {}, _current_frame )
		if isclass( args[0] ):
			return args[0]

	return _inner

def register( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

def register_1( *args, **kwargs ):
	return _register( *args, **(kwargs | {'_current_frame': currentframe() } ) )

@register
def f_01():
	REGISTRY.call_counter += 1

@register( 'arg_01' )
def f_02():
	REGISTRY.call_counter += 1

@register( param='param_01' )
def f_03():
	REGISTRY.call_counter += 1

@register( 'arg_02', param='param_02' )
def f_04():
	REGISTRY.call_counter += 1

@register_1
class C01:
	...

@register_1( 'arg_01' )
class C02:
	...

@register_1( param='param_01' )
class C03:
	...

@register_1( 'arg_02', param='param_02' )
class C04:
	...

def test_decorators_2():
	assert len( REGISTRY.decorators ) == 8
	assert REGISTRY.call_counter == 0

	callers = [ d.caller_name for d in REGISTRY.decorators ]
	assert callers == ['register', 'register', 'register', 'register', 'register_1', 'register_1', 'register_1', 'register_1']

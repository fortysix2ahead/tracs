# sample code for generic decorating:
from inspect import isclass, isfunction

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
			if isfunction( args[0] ):
				return args[0]()
			elif isclass( args[0] ):
				return args[0].__new__( args[0] )
			else:
				raise RuntimeError( 'should not happen!' )

	if args and not kwargs and ( isfunction( args[0] ) or isclass( args[0] ) ):
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

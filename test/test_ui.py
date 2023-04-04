
from copy import deepcopy
from pytest import mark
from time import sleep

from rich.console import Console

from tracs.config import ApplicationContext
from tracs.ui import diff_table

@mark.file( 'libraries/default/polar/1/0/0/100001/100001.json' )
def test_diff_dict( json ):
	json1, json2 = deepcopy( json ), deepcopy( json )
	json1['country'] = 'Germany'
	json2['title'] = 'Hamburg'
	json2['route'] = 'Along the Sea'

	Console().print( diff_table( json1, json2 ) )

@mark.skip
def test_progress_bar():
	ctx = ApplicationContext()

	# test with number of steps
	ctx.start( 'task description', 1000 )
	for i in range( 1000 ):
		ctx.advance( f'position in range: {i}' )
		sleep( 0.0008 )
	ctx.complete()

	# test with infinite number of steps
	ctx.start( 'task description' )
	for i in range( 1000 ):
		ctx.advance( f'position in range: {i}' )
		sleep( 0.0008 )
	ctx.complete()

	ctx.verbose = True
	# test with number of steps
	ctx.start( 'task description', 10 )
	for i in range( 10 ):
		ctx.advance( f'position in range: {i}' )
		sleep( 0.0008 )
	ctx.complete()

if __name__ == '__main__':
	test_progress_bar()

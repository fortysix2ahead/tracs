from copy import deepcopy

from pytest import mark

from rich.console import Console

from tracs.ui import diff_table

@mark.file( 'library/polar/1/0/0/100001/100001.raw.json' )
def test_diff_dict( json ):
	json1, json2 = deepcopy( json ), deepcopy( json )
	json1['country'] = 'Germany'
	json2['title'] = 'Hamburg'
	json2['route'] = 'Along the Sea'

	Console().print( diff_table( json1, json2 ) )


from datetime import datetime

from pytest import raises

from tracs.dataclasses import BaseDocument

# test BaseDocument as the DataClass class is not of much use as it does not contain any fields
def test_dataclass_document():
	bd = BaseDocument()
	assert bd.doc_id == 0 and bd['doc_id'] == 0 and 'doc_id' in bd
	assert bd.id == 0 and bd['id'] == 0 and 'id' in bd

	bd = BaseDocument( { 'value': 1 } )
	assert 'value' not in bd
	with raises( AttributeError ):
		assert bd.value == 1

	bd = BaseDocument( { 'value': 1 }, 20 )
	assert 'value' not in bd
	assert bd['doc_id'] == 20 and bd.doc_id == 20

	with raises( TypeError ):
		BaseDocument( { 'value': 1 }, some_value=20 )  # this leads to unexpected keyword argument

	# provided doc_id
	bd = BaseDocument( doc_id = 10 )
	assert bd['doc_id'] == 10 and bd.doc_id == 10

	# constructor with a dict and the doc_id as kwarg
	bd = BaseDocument( { 'value': 1 }, doc_id=10 )
	assert 'value' not in bd
	assert bd['doc_id'] == 10 and bd.doc_id == 10

def test_contains():
	bd = BaseDocument( { 'value': 1 }, 10 )

	assert 'value' not in bd
	assert not bd.hasattr( 'value' )

	assert bd.hasattr( 'doc_id' )
	assert 'doc_id' in bd

def test_get():
	tcd = BaseDocument()
	assert tcd._values_for( 'doc_id' ) == (0, 0, 0)

	dcd = BaseDocument( { 'value': 1 }, 10 )
	assert dcd._values_for( 'doc_id' ) == (10, 10, 10)
	assert dcd._values_for( 'value' ) == (None, None, None)

def test_keys_values_items():
	tcd = BaseDocument( { 'value': 1 }, 10 )

	assert 'doc_id' in list( tcd.keys() )
	assert 10 in tcd.values()
	assert ('doc_id', 10) in list( tcd.items() )

def test_testdataclass():
	# default empty document
	tcd = BaseDocument()
	assert tcd._values_for( 'id' ) == (0, 0, 0)
	assert tcd._values_for( 'name' ) == (None, None, None)

	# setting an attribute
	tcd.id = 20
	assert tcd._values_for( 'id' ) == (20, 20, 20)
	tcd['id'] = 30
	assert tcd._values_for( 'id' ) == (30, 30, 30)

	assert 'id' in tcd and tcd.hasattr( 'id' )
	assert 'undeclared' not in tcd and not tcd.hasattr( 'undeclared' )

	# declared attribute as argument -> this is also available in data -> do we want this?
	tcd = BaseDocument( id = 30 )
	assert tcd._values_for( 'id' ) == (30, 30, 30)

	# declared attribute in dict override default
	tcd = BaseDocument( { 'id': 20 } )
	assert tcd._values_for( 'id' ) == (20, 20, 20)

	# undeclared attribute as argument -> this fails
	with raises( TypeError ):
		tcd = BaseDocument( undeclared=10 )

	# undeclared attribute in dict
	tcd = BaseDocument( { 'undeclared': 10 } )
	assert tcd._values_for( 'undeclared' ) == (None, None, None)

def test_testdataclass_asdict():
	tcd = BaseDocument()
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}

	tcd.id = 20
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}

	tcd['id'] = 30
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}

	tcd = BaseDocument( id=30 )
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}
	tcd = BaseDocument( { 'id': 20 } )
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}

	tcd = BaseDocument( { 'undeclared': 10 } )
	assert tcd.asdict() == {'classifier': None, 'raw_id': 0}

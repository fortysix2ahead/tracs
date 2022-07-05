
from pytest import raises

from tracs.dataclasses import as_dict
from tracs.dataclasses import attr_for
from tracs.dataclasses import BaseDocument

# test BaseDocument as the DataClass class is not of much use as it does not contain any fields
def test_dataclass_document():
	bd = BaseDocument()
	assert bd.doc_id == 0 and bd['doc_id'] == 0 and 'doc_id' in bd
	assert bd.id == 0 and bd['id'] == 0 and 'id' in bd

	bd = BaseDocument( {'value': 1} )
	assert 'value' not in bd
	with raises( AttributeError ):
		assert bd.value == 1

	bd = BaseDocument( {'value': 1}, 20 )
	assert 'value' not in bd
	assert bd['doc_id'] == 20 and bd.doc_id == 20

	with raises( TypeError ):
		BaseDocument( {'value': 1}, some_value=20 )  # this leads to unexpected keyword argument

	# provided doc_id
	bd = BaseDocument( doc_id=10 )
	assert bd['doc_id'] == 10 and bd.doc_id == 10

	# constructor with a dict and the doc_id as kwarg
	bd = BaseDocument( {'value': 1}, doc_id=10 )
	assert 'value' not in bd
	assert bd['doc_id'] == 10 and bd.doc_id == 10


def test_contains():
	bd = BaseDocument( {'value': 1}, 10 )

	assert 'value' not in bd
	assert not bd.hasattr( 'value' )

	assert bd.hasattr( 'doc_id' )
	assert 'doc_id' in bd


def test_get():
	bd = BaseDocument()
	assert bd._values_for( 'doc_id' ) == (0, 0, 0)

	bd = BaseDocument( {'value': 1}, 10 )
	assert bd._values_for( 'doc_id' ) == (10, 10, 10)
	assert bd._values_for( 'value' ) == (None, None, None)


def test_keys_values_items():
	bd = BaseDocument( {'value': 1}, 10 )

	assert 'doc_id' in list( bd.keys() )
	assert 10 in bd.values()
	assert ('doc_id', 10) in list( bd.items() )


def test_testdataclass():
	# default empty document
	bd = BaseDocument()
	assert bd._values_for( 'id' ) == (0, 0, 0)
	assert bd._values_for( 'name' ) == (None, None, None)

	# setting an attribute
	bd.id = 20
	assert bd._values_for( 'id' ) == (20, 20, 20)
	bd['id'] = 30
	assert bd._values_for( 'id' ) == (30, 30, 30)

	assert 'id' in bd and bd.hasattr( 'id' )
	assert 'undeclared' not in bd and not bd.hasattr( 'undeclared' )

	# declared attribute as argument -> this is also available in data -> do we want this?
	bd = BaseDocument( id=30 )
	assert bd._values_for( 'id' ) == (30, 30, 30)

	# declared attribute in dict override default
	bd = BaseDocument( {'id': 20} )
	assert bd._values_for( 'id' ) == (20, 20, 20)

	# undeclared attribute as argument -> this fails
	with raises( TypeError ):
		bd = BaseDocument( undeclared=10 )

	# undeclared attribute in dict
	bd = BaseDocument( {'undeclared': 10} )
	assert bd._values_for( 'undeclared' ) == (None, None, None)


def test_testdataclass_asdict():
	bd = BaseDocument()
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}
	bd.id = 20
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}
	bd['id'] = 30
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}

	bd = BaseDocument( id=30 )
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}
	bd = BaseDocument( {'id': 20} )
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}
	bd = BaseDocument( {'undeclared': 10} )
	assert bd.asdict() == {'classifier': None, 'raw_id': 0}

def test_attr_for():
	attrs = BaseDocument().__attrs_attrs__
	assert attr_for( attributes=attrs, key='uid' ) is not None
	assert attr_for( attributes=attrs, key='uuid' ) is None

def test_as_dict():
	bd = BaseDocument()
	assert as_dict( bd ) == {'raw_id': 0}

	bd = BaseDocument( data={'k': 'v'} )

	assert as_dict( bd, remove_data_field=False ) == {'raw_id': 0}

	assert as_dict( bd, remove_persist_fields=False, remove_data_field=True ) == {
		'doc_id': 0,
		'id': 0,
		'raw_id': 0,
		'uid': 'base:0'
	}

	assert as_dict( bd, remove_persist_fields=False, remove_data_field=False ) == {
		'data': {'k': 'v'},
		'doc_id': 0,
		'id': 0,
		'raw_id': 0,
		'uid': 'base:0'
	}

	assert as_dict( bd, remove_persist_fields=False, remove_null_fields=False, remove_data_field=True ) == {
		'classifier': None,
		'dataclass' : None,
		'doc_id'    : 0,
		'id'        : 0,
		'raw'       : None,
		'raw_data'  : None,
		'raw_id'    : 0,
		'raw_name'  : None,
		'service'   : None,
		'uid'       : 'base:0'
	}
	assert as_dict( bd, remove_persist_fields=False, remove_null_fields=False, remove_data_field=False ) == {
		'classifier': None,
		'data'      : {'k': 'v'},
		'dataclass' : None,
		'doc_id'    : 0,
		'id'        : 0,
		'raw'       : None,
		'raw_data'  : None,
		'raw_id'    : 0,
		'raw_name'  : None,
		'service'   : None,
		'uid'       : 'base:0'
	}


from dataclasses import InitVar
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from datetime import datetime
from typing import ClassVar

from pytest import raises

from tracs.dataclasses import as_dict
from tracs.dataclasses import BaseDocument

# test BaseDocument as the DataClass class is not of much use as it does not contain any fields
def test_dataclass_document():
	bd = BaseDocument()
	assert bd.doc_id == 0 and bd['doc_id'] == 0 and 'doc_id' in bd
	assert bd.id == 0 and bd['id'] == 0 and 'id' in bd
	with raises( AttributeError ):
		test = bd.undeclared
	assert bd.get( 'undeclared' ) is None

	bd = BaseDocument( { 'undeclared': 1 } )
	with raises( AttributeError ):
		test = bd.undeclared
	assert bd.get( 'undeclared' ) is None
	assert 'undeclared' not in bd

	bd = BaseDocument( {'undeclared': 1}, 20 )
	assert 'undeclared' not in bd
	assert bd['doc_id'] == 20 and bd.doc_id == 20

	with raises( TypeError ):
		BaseDocument( {'value': 1}, undeclared=20 )  # this leads to unexpected keyword argument

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

#def test_keys_values_items():
#	bd = BaseDocument( {'value': 1}, 10 )
#	assert 'doc_id' in list( bd.keys() )
#	assert 10 in bd.values()
#	assert ('doc_id', 10) in list( bd.items() )

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
	assert bd.asdict() == {}
	bd.id = 20
	assert bd.asdict() == {}
	bd['id'] = 30
	assert bd.asdict() == {}

	bd = BaseDocument( id=30 )
	assert bd.asdict() == {}
	bd = BaseDocument( {'id': 20} )
	assert bd.asdict() == {}
	bd = BaseDocument( {'undeclared': 10} )
	assert bd.asdict() == {}

def test_as_dict():
	bd = BaseDocument()
	assert as_dict( bd ) == {}
	assert as_dict( bd, remove_protected=True ) == {}

	bd.data= { 'k': 'v' }

	assert as_dict( bd, remove_persist=False, remove_data=True ) == {
		'dirty': False,
		'doc_id': 0,
		'id': 0,
	}

	assert as_dict( bd, remove_persist=False, remove_data=False ) == {
		'data': {'k': 'v'},
		'dirty': False,
		'doc_id': 0,
		'id': 0
	}

	assert as_dict( bd, remove_persist=False, remove_null=False, remove_data=True ) == {
		'dirty'     : False,
		'doc_id'    : 0,
		'id'        : 0
	}

	assert as_dict( bd, remove_persist=False, remove_null=False, remove_data=False ) == {
		'data'      : {'k': 'v'},
		'dirty'     : False,
		'doc_id'    : 0,
		'id'        : 0
	}

# just some additional tests to get used to dataclass features

class DatetimeDescriptor:

	def __init__( self, *, default ):
		self._default = default

	def __set_name__( self, owner, name ):
		self._name = "_" + name

	def __get__( self, obj, type ):
		if obj is None:
			return self._default
		return getattr( obj, self._name, self._default )

	def __set__( self, obj, value ):
		setattr( obj, self._name, datetime.fromisoformat( value ) if value else None )

@dataclass
class TestDataClass:

	decoder: ClassVar[str] = field( default='json' )
	# initializer: InitVar[str] = field( default='nothing' )
	initializer: InitVar[str] = 'nothing'
	internal: str = field( default=None )

	# this enables auto-conversions ...
	time: DatetimeDescriptor = DatetimeDescriptor( default=None )

	def __post_init__( self, initializer ):
		if initializer:
			self.internal = initializer.lower()

def test_tdc():

	tdc = TestDataClass()
	assert 'decoder' not in fields( tdc )
	assert TestDataClass.decoder == 'json'

	tdc = TestDataClass( initializer='INIT' )
	assert tdc.internal == 'init'
	assert tdc.initializer == 'nothing' # not sure why the field is accessible

	tdc.time = datetime.utcnow().isoformat()
	assert type( tdc.time ) is datetime


from gtrac.group import group_activities
from gtrac.group import ungroup_activities

def test_grouping( db ):
	_all = db.all( True, True, True )
	a51 = db.get( doc_id=51 )
	a52 = db.get( doc_id=52 )
	a53 = db.get( doc_id=53 )
	a54 = db.get( doc_id=54 )
	a55 = db.get( doc_id=55 )

	group_activities( [a51, a52, a53, a54, a55], True, True )

	ag = db.get( doc_id=56 )
	assert ag is not None
	assert ag.is_group
	assert ag.group_for == [ 51, 52, 53 ]

	ag = db.get( doc_id=57 )
	assert ag is not None
	assert ag.is_group
	assert ag.group_for == [54, 55]

def test_ungroup( db ):
	assert db.get( doc_id=1 ).is_group
	assert db.get( doc_id=2 ).grouped_by == 1
	assert db.get( doc_id=3 ).grouped_by == 1
	assert db.get( doc_id=4 ).grouped_by == 1

	ungroup_activities( [db.get( doc_id=1 )], True, True )

	assert db.get( doc_id=1 ) is None
	assert db.get( doc_id=2 ).grouped_by is None
	assert db.get( doc_id=3 ).grouped_by is None
	assert db.get( doc_id=4 ).grouped_by is None

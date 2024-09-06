from datetime import datetime

from pytest import mark

from test.conftest import Environment
from tracs.activity import Activity
from tracs.config import ApplicationContext
from tracs.group import group_activities2
from tracs.group import ungroup_activities
from tracs.registry import Registry

@mark.xfail # todo: needs improvement
def test_group_activities():
	a1 = Activity( name='a1', starttime=datetime( 2022, 2, 22, 10, 0, 0 ), uid='a:1', heartrate_max=180 )
	a2 = Activity( name='a2', starttime=datetime( 2022, 2, 22, 10, 0, 1 ), uid='a:2', heartrate=150 )
	a3 = Activity( name='a3', starttime=datetime( 2022, 2, 22, 14, 0, 0 ), uid='a:3' )
	a4 = Activity( name='a4', starttime=datetime( 2022, 2, 22, 14, 0, 1 ), uid='a:4' )
	a5 = Activity( name='a5', starttime=datetime( 2022, 2, 22, 14, 0, 2 ), uid='a:5' )
	a6 = Activity( name='a6', starttime=datetime( 2022, 2, 22, 17, 0, 0 ), uid='a:6' )

	groups = group_activities2( [a3, a2, a6, a1, a4, a5] )

	assert len( groups ) == 2
	g1, g2 = groups
	assert g1.members == [a1, a2]
	assert g2.members == [a3, a4, a5]

	g1.execute()
	assert g1.head.starttime == a1.starttime and g1.head.name == a1.name
	assert g1.head.heartrate_max == a1.heartrate_max and g1.head.heartrate == a2.heartrate

@mark.context( env='default', persist='clone', cleanup=True )
def test_ungroup_activities( env: Environment ):
	env.db.register_summary_types( *[ rt.type for rt in Registry.instance().resource_types.values() if rt.summary ] )
	g = env.db.get_by_id( 2001 )
	result = ungroup_activities( env.ctx, [g], force=True )

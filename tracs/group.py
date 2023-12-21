
from datetime import datetime, time, timedelta
from logging import getLogger
from typing import List, Optional, Tuple

from attrs import define, field
from rich.prompt import Confirm

from tracs.service import Service
from tracs.activity import Activity, ActivityPart, groups
from tracs.fsio import ACTIVITIES_CONVERTER
from tracs.config import ApplicationContext
from tracs.ui import Choice, dict_table, diff_table_3
from tracs.utils import seconds_to_time, unique_sorted as usort

log = getLogger( __name__ )

DELTA = 180
MAX_DELTA = timedelta( seconds=180 )
PART_THRESHOLD = 4

@define
class ActivityGroup:

	members: List[Activity] = field( factory=list )
	time: datetime = field( default=None )

	@property
	def head( self ) -> Activity:
		return self.members[0]

	@property
	def tail( self ) -> List[Activity]:
		return self.members[1:]

	def execute( self ):
		self.head.union( self.tail )
		self.head.uids = usort( [ a.uid for a in self.members ] )
		self.head.uid = sorted( [ a.starttime for a in self.members ] )[0].strftime( 'group:%y%m%d%H%M%S' )

def group_activities( ctx: ApplicationContext, activities: List[Activity], force: bool = False ) -> None:
	groups = group_activities2( activities )

	for g in groups:
		updated, removed = [], []
		if force or confirm_grouping( ctx, g ):
			g.execute()
			updated.append( g.head )
			removed.extend( g.tail )

		# ctx.db.upsert_activities( updated ) # this is not necessary, activity is already updated
		ctx.db.remove_activities( removed )
		ctx.db.commit()

def group_activities2( activities: List[Activity] ) -> List[ActivityGroup]:
	last_activity, next_activity, current_group = None, None, None
	groups: List[ActivityGroup] = []
	for a in sorted( activities, key=lambda act: act.starttime.timestamp() ):
		last_activity, next_activity = next_activity, a
		if last_activity is None:
			current_group = ActivityGroup( members=[a], time=a.starttime )
			continue

		delta = next_activity.starttime - last_activity.starttime
		if delta < MAX_DELTA:
			current_group.members.append( a )
		else:
			groups.append( current_group )
			current_group = ActivityGroup( members=[a], time=a.starttime )

	# append the last group
	if current_group:
		groups.append( current_group )

	return [g for g in groups if len( g.members ) > 1 ]

def confirm_grouping( ctx: ApplicationContext, group: ActivityGroup, force: bool = False ) -> bool:
	if force:
		return True

	result = ACTIVITIES_CONVERTER.unstructure( group.head.union( group.tail, copy=True ), Activity )
	result['uids'] = sorted( list( { *group.head.uids, *[uid for t in group.tail for uid in t.uids] } ) )
	sources = [ACTIVITIES_CONVERTER.unstructure( a, Activity ) for a in group.members]

	ctx.console.print( diff_table_3( result = result, sources = sources ) )

	answer = Confirm.ask( f'Continue grouping?' )
	names = sorted( list( set( [member.name for member in group.members] ) ) )
	if answer and len( names ) > 1:
		headline = 'Select a name for the new activity group:'
		choices = names
		group.head.name = Choice.ask( headline=headline, choices=choices, use_index=True, allow_free_text=True )

	return answer

# ---------------------

def ungroup_activities( ctx: ApplicationContext,
                        activities: List[Activity],
                        keep: bool = False,
                        force: bool = False,
                        pretend: bool = False ) -> Optional[Tuple[List[Activity], List[Activity]]]:
	"""
	Ungroups activities
	:param ctx: context
	:param activities: groups to be ungrouped
	:param keep: keeps the groups, do not remove them from the db
	:param force: do not ask for permission
	:param pretend: when true does not persist changes to db
	:return:
	"""
	all_groups, all_members = [], []
	for a in groups( activities ):
		if force or Confirm.ask( f'Ungroup activity {a.id} ({a.name})?' ):
			# members = [Service.as_activity( ctx.db.get_summary( uid ) ) for uid in a.uids]
			members = [ Service.as_activity( r ) for r in ctx.db.find_all_summaries( a.uids ) ]
			all_groups.append( a )
			all_members.extend( members )
			log.debug( f'ungrouped activity {a.uid}, containing members {a.uids}' )

	# persist changes
	if not pretend:
		if not keep:
			ctx.db.remove_activities( all_groups )
		ctx.db.insert_activities( all_members )
		ctx.db.commit()

	return all_groups, all_members

# parting / unparting

def part_activities( activities: List[Activity], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ):
	# experimental warning ... todo: remove later
	if len( activities ) > PART_THRESHOLD:
		log.warning( f'experimental: not going to create multipart activity consisting of more than {PART_THRESHOLD} activities' )
		return

	# todo: prerequisite check? time + time_end must exist

	activities.sort( key=lambda e: e.starttime )

	parts, gaps = [], []
	for a in activities:
		try:
			last = parts[-1]
			gap = a.starttime - last.endtime
			if gap.total_seconds() > 0:
				parts.append( a )
				gaps.append( seconds_to_time( gap.total_seconds() ) )
			else:
				log.warning( f'activities {a.id} and {last.id} overlap, skipping grouping as multipart' )
		except IndexError:
			parts.append( a )
			gaps.append( time( 0 ) )

	part_list = [ ActivityPart( uids=p.uids, gap=g ) for p, g in zip( parts, gaps ) ]
	new_activity = Activity( parts=part_list, other_parts=activities )
	if force or _confirm_part( ctx, new_activity ):
		id = ctx.db.insert( new_activity )
		ctx.console.print( f'Created new activity {id}' )
		ctx.db.commit()

def _confirm_part( ctx: ApplicationContext, activity: Activity ) -> bool:
	dump = ctx.db.factory.dump( activity, Activity )
	ctx.console.print( f'Going to create a new multipart activity consisting of {len( activity.parts )} parts:' )
	ctx.console.print( dict_table( dump, sort_entries=True ) )
	return Confirm.ask( f'Continue?' )

def unpart_activities( activities: List[Activity], force: bool = False, pretend: bool = False, ctx: ApplicationContext = None ):
	activities = [a for a in activities if a.multipart]
	ids = [a.id for a in activities]
	if force or Confirm.ask( f'Going to remove multipart activities {ids}' ):
		ctx.db.remove_activities( activities, auto_commit=True )

def validate_parts( activities: [Activity], force: bool ) -> bool:
	return True

# helper functions

def _delta( target_time: datetime, src_time: datetime ) -> Tuple[bool, float]:
	delta = (src_time - target_time).total_seconds()
	if -DELTA < delta < DELTA:
		return True, delta
	else:
		return False, delta

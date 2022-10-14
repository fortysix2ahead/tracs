
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from click import echo
from logging import getLogger
from rich.prompt import Confirm

from .activity import Activity
from .config import ApplicationContext
from .config import KEY_GROUPS as GROUPS
from .config import console
from .dataclasses import as_dict
from .plugins.groups import ActivityGroup
from .ui import Choice
from .ui import diff_table2

log = getLogger( __name__ )

DELTA = 180

@dataclass
class GroupResult:

	time: datetime = field( default=None )
	target: Activity = field( default=None )
	members: List[Activity] = field( default_factory=list )

@dataclass
class Bucket:

	day: int = field( default=None )
	queue: List[Activity] = field( default_factory=list )
	targets: List[GroupResult] = field( default_factory=list )

def group_activities( ctx: ApplicationContext, activities: List[Activity], force: bool = False, pretend: bool = False ) -> None:
	log.debug( f'attempting to group {len( activities )} activities' )

	changes: List[Activity] = []
	removals: List[Activity] = []
	buckets: Dict[int, Bucket] = {}

	for a in activities:
		day = int( a.time.strftime( '%y%m%d' ) )
		if not day in buckets:
			buckets[day] = Bucket( day=day )
		buckets[day].queue.append( a )

	log.debug( f'sorted activities into {len( buckets.keys() )} buckets, based on day of activity' )

	for key, bucket in buckets.items():
		log.debug( f'analysing bucket {key}' )
		if len( bucket.queue ) <= 1: # skip days with only one activity -> there's nothing to group
			continue

		for src in bucket.queue: # src means activity to be merged into a group
			# check if we find a matching target group for the ungrouped activity ua
			target = None  # target group
			for t in bucket.targets:
				delta_result, delta_time = _delta( t.time, src.time )
				if delta_result:
					target = t
					break

			# create new target group when nothing is found
			if target:
				target.members.append( src )
			else:
				bucket.targets.append( GroupResult( time=src.time, members=[ src ] ) )

	# now perform the actual (interactive) grouping
	for key, bucket in buckets.items():
		for t in bucket.targets:
			if len( t.members ) > 0:
				t.target = Activity()
				for m in t.members:
					t.target.init_from( m )
					t.target.uids.extend( m.uids )

				if force or _confirm_grouping( t ):
					changes.append( t.members[0] )
					for m in t.members[1:]:
						t.members[0].init_from( m )
						t.members[0].uids.extend( m.uids )
						removals.append( m )

	if not pretend:
		for c in changes: ctx.db.update( c )
		for r in removals: ctx.db.remove( r )

def _confirm_grouping( gr: GroupResult ) -> bool:
	echo( f"Attempting to group activities:" )

	table = diff_table2( result = as_dict( gr.target ), sources = [ as_dict( m ) for m in gr.members] )
	console.print( table )

	answer = Confirm.ask( f'Continue grouping?' )

	names = list( set( [member.name for member in [gr.target] + gr.members ] ) )
	if answer and len( names ) > 1:
		headline = 'Select a name for the new activity group:'
		choices = names
		gr.members[0].name = Choice.ask( headline=headline, choices=choices, use_index=True, allow_free_text=True )

	return answer

# ---------------------

def ungroup_activities( ctx: ApplicationContext, activities: List[Activity], force: bool = False, pretend: bool = False ) -> Optional[Tuple[List[Activity], List[Activity]]]:
	"""
	Ungroups activities
	:param ctx: context
	:param activities: groups to be ungrouped
	:param force: do not ask for permission
	:param pretend: when true does not persist changes to db
	:return:
	"""
	ungrouped_parents = []
	ungrouped_children = []
	for a in activities:
		if a.is_group:
			grouped = [ ctx.db.get( doc_id=id ) for id in a.group_for ]
			if not force:
				answer = Confirm.ask( f'Ungroup activity {a.id} ({a.name})?' )
			else:
				answer = True

			if answer:
				_ungroup( a, grouped )
				ungrouped_parents.append( a )
				ungrouped_children.extend( grouped )
				log.debug( f'ungrouped activity {a.id}' )

	# persist changes
	if not pretend:
		for a in ungrouped_parents:
			ctx.db.remove( a )
		for a in ungrouped_children:
			ctx.db.remove_field( a, GROUPS )
	else:
		return ungrouped_parents, ungrouped_children

# parting / unparting

def part_activities( activities: [Activity], force: bool ):
	if validate_parts( activities ) or force:
		pass

def unpart_activities( activities: [Activity], force: bool ):
	pass

def validate_parts( activities: [Activity], force: bool ) -> bool:
	return True

# helper functions

def _delta( target_time: datetime, src_time: datetime ) -> Tuple[bool, float]:
	delta = (src_time - target_time).total_seconds()
	if -DELTA < delta < DELTA:
		return True, delta
	else:
		return False, delta

def _new_group( children: [Activity] ) -> ActivityGroup:
	ids = list( [c.doc_id for c in children] )
	uids = list( [c['uid'] for c in children] )
	return ActivityGroup( group_ids=ids, group_uids=uids )

def _ungroup( parent: Activity, children: [Activity] ) -> None:
	del parent[GROUPS]
	for c in children:
		del c[GROUPS]

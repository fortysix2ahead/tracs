
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from click import echo
from dateutil.tz import tzlocal
from dateutil.tz import UTC
from logging import getLogger
from sys import exit as sysexit

from rich.table import Table

from .activity import Activity
from .config import KEY_GROUPS as GROUPS
from .config import GlobalConfig as gc
from .config import console
from .plugins.groups import ActivityGroup
from .utils import colored_diff
from .utils import fmt

log = getLogger( __name__ )

@dataclass
class GroupResult:

	target: Activity = field( default=None )
	members: List[Activity] = field( default_factory=list )

@dataclass
class Bucket:

	day: int = field( default=None )
	queue: List[Activity] = field( default_factory=list )
	targets: List[GroupResult] = field( default_factory=list )

def group_activities( activities: List[Activity], force: bool = False, pretend: bool = False ) -> List[Tuple[Activity, List[Activity]]]:
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
				delta_res, delta_time, delta_ask = _delta( t.target.time, src.time )
				if delta_res:
					target = t
					break

			# create new target group when nothing is found
			if target:
				target.members.append( src )
			else:
				bucket.targets.append( GroupResult( target=src ) )

	# now perform the actual (interactive) grouping
	for key, bucket in buckets.items():
		for t in bucket.targets:
			if t.target and len( t.members ) > 0:
				if force or _confirm_grouping( t ):
					for m in t.members:
						t.target.init_from( m )
						t.target.uids.extend( m.uids )
						changes.append( t.target )
						removals.append( m )

	if not pretend:
		for c in changes: gc.db.update( c )
		for r in removals: gc.db.remove( r )

def _confirm_grouping(  gr: GroupResult ) -> bool:
	echo( f"Attempting to group activities:" )
	left = {
		'Name': gr.target.name,
		'Type': fmt( gr.target.type ),
		'Localtime': fmt( gr.target.localtime ),
		'Time': fmt( gr.target.time ),
		'Elapsed Time': fmt( gr.target.duration ),
		'Distance': fmt( gr.target.distance ),
	}
	rights = []
	for m in gr.members:
		right = {
				'Name': m.name,
				'Type': fmt( m.type ),
				'Localtime': fmt( m.localtime ),
				'Time': fmt( m.time ),
				'Elapsed Time': fmt( m.duration ),
				'Distance': fmt( m.distance ),
			}
		rights.append( right )

	table = Table( box=None, show_header=False, show_footer=False )
	for key, value in left.items():
		row = [ key, value ]
		for r in rights:
			left, right = colored_diff( value, r.get( key ) )
			row.append( right )
		table.add_row( *row )

	console.print( table )

	answer = qconfirm( f'Continue grouping?', default=False, qmark='', auto_enter=True ).ask()
	if answer is None:
		sysexit( -1 )
	else:
		return answer

def _ask_for_name( children: [Activity], force: bool ) -> str:
	if not force:
		names = sorted( { *[c['name'] for c in children] } )
		if len( names ) > 1:
			answer = qselect(
				'Which name should be used for the grouped activity?',
				choices=names,
				qmark='',
				use_shortcuts=True
			).ask()

			if answer is None:
				sysexit( -1 )
			else:
				return answer
		else:
			return names[0]
	else:
		return children[0]['name']

def _ask_for_type( children: [Activity], force: bool ) -> str:
	if not force:
		types = sorted( { *[c['type'] for c in children] } )
		if len( types ) > 1:
			answer = qselect(
				'Which type should be used for the grouped activity?',
				choices=types,
				qmark='',
				use_shortcuts=True
			).ask()

			if answer is None:
				sysexit( -1 )
			else:
				return answer
		else:
			return types[0]
	else:
		return children[0]['type']

# ---------------------

def ungroup_activities( activities: [Activity], force: bool, persist_changes = True ) -> Optional[Tuple[List[Activity], List[Activity]]]:
	"""
	Ungroups activities
	:param activities: groups to be ungrouped
	:param force: do not ask for permission
	:param persist_changes: when true does not persist changes to db, instead return changed activities
	:return:
	"""
	ungrouped_parents = []
	ungrouped_children = []
	for a in activities:
		if a.is_group:
			grouped = [ gc.db.get( doc_id=id ) for id in a.group_for ]
			if not force:
				answer = qconfirm( f'Ungroup activity {a.id} ({a.name})?', default=False, qmark='', auto_enter=True ).ask()
			else:
				answer = True

			if answer:
				_ungroup( a, grouped )
				ungrouped_parents.append( a )
				ungrouped_children.extend( grouped )
				log.debug( f'ungrouped activity {a.id}' )

	# persist changes
	if persist_changes:
		for a in ungrouped_parents:
			gc.db.remove( a )
		for a in ungrouped_children:
			gc.db.remove_field( a, GROUPS )
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

def _delta( target_time: datetime, src_time: datetime ) -> Tuple[bool, float, bool]:
	delta = (src_time - target_time).total_seconds()
	# delta 2/3: assume that one activity reports localtime as UTC
	delta2 = (src_time - target_time.replace( tzinfo=tzlocal() ).astimezone( UTC )).total_seconds()
	delta3 = (src_time.replace( tzinfo=tzlocal() ).astimezone( UTC ) - target_time).total_seconds()
	if -60 < delta < 60:
		return True, delta, False
	elif (-60 < delta2 < 60) or (-60 < delta3 < 60):
		delta = delta2 if abs( delta2 ) < abs( delta3 ) else delta3
		return True, delta, True
	else:
		return False, delta, False

def _new_group( children: [Activity] ) -> ActivityGroup:
	ids = list( [c.doc_id for c in children] )
	uids = list( [c['uid'] for c in children] )
	return ActivityGroup( group_ids=ids, group_uids=uids )

def _ungroup( parent: Activity, children: [Activity] ) -> None:
	del parent[GROUPS]
	for c in children:
		del c[GROUPS]

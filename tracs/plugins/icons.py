
from __future__ import annotations

from tracs.activity import Activity
from tracs.activity_types import ActivityTypes
from tracs.registry import virtualfield

DEFAULT_CLASSIFIER_ICON = '\u2bbe'
DEFAULT_TYPE_ICON = ':running_shoe:'

CLASSIFIER_ICONS = {
	'bikecitizens': '[bright_red]\u24b7[/bright_red]',
	'polar': '[bright_blue]\u24c5[/bright_blue]',
	'strava': '[orange1]\u24c8[/orange1]',
	'waze': '[bright_cyan]\u24cc[/bright_cyan]',
}

TYPE_ICONS = {
	ActivityTypes.bike: ':bicycle:',
	ActivityTypes.drive: ':car:',
	ActivityTypes.gym: ':person_lifting_weights:',
	ActivityTypes.hiking: ':hiking_boot:',
	ActivityTypes.rollski: ':ski:',
	ActivityTypes.rollski_classic: ':ski:',
	ActivityTypes.rollski_free: ':ski:',
	ActivityTypes.run: ':running:',
	ActivityTypes.ski: ':ski:',
	ActivityTypes.xcski_classic: ':ski:',
	ActivityTypes.xcski_free: ':ski:',
}

@virtualfield
def icons( a: Activity ) -> str:
	return '  '.join( [
		TYPE_ICONS.get( a.type, DEFAULT_TYPE_ICON ),
		*[ CLASSIFIER_ICONS.get( c, DEFAULT_CLASSIFIER_ICON ) for c in a.classifiers]
	] )

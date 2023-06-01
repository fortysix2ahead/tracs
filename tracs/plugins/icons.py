
from __future__ import annotations

from tracs.activity import Activity
from tracs.registry import virtualfield

CLASSIFIER_ICONS = {
	'_default': '\u2bbe',
	'bikecitizens': '[bright_red]\u24b7[/bright_red]',
	'polar': '[bright_blue]\u24c5[/bright_blue]',
	'strava': '[orange1]\u24c8[/orange1]',
	'waze': '[bright_cyan]\u24cc[/bright_cyan]',
}

@virtualfield
def classifier_icons( a: Activity ) -> str:
	return ' '.join( [ CLASSIFIER_ICONS.get( c, CLASSIFIER_ICONS.get( '_default' ) ) for c in a.classifiers] )

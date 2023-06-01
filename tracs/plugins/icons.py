
from __future__ import annotations

from tracs.activity import Activity
from tracs.registry import virtualfield

CLASSIFIER_ICONS = {
	'_default': '\u2bbe',
	'bikecitizens': '\u24b7',
	'polar': '\u24c5',
	'strava': '\u24c8',
	'waze': '\u24cc',
}

@virtualfield
def classifier_icons( a: Activity ) -> str:
	return ''.join( [ CLASSIFIER_ICONS.get( c, CLASSIFIER_ICONS.get( '_default' ) ) for c in a.classifiers] )

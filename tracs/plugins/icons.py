
from __future__ import annotations

from typing import List

from tracs.activity import Activity
from tracs.registry import virtualfield

CLASSIFIER_ICONS = {
	'_default': '_',
	'bikecitizens': 'B',
	'polar': 'P',
	'strava': 'S',
	'waze': 'W',
}

@virtualfield
def classifier_icons( a: Activity ) -> List[str]:
	return [ CLASSIFIER_ICONS.get( c, CLASSIFIER_ICONS.get( '_default' ) ) for c in a.classifiers]

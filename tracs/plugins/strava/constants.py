
from re import compile

from tracs.activity_types import ActivityTypes

STRAVA_TYPE = 'application/vnd.strava+json'

BASE_URL = 'https://www.strava.com'
OAUTH_REDIRECT_URL = 'http://localhost:40004'
SCOPE = 'activity:read_all'

FETCH_PAGE_SIZE = 30 #
PHOTO_SIZE = 2800

TIMEZONE_FULL_REGEX = compile( r'^(\(.+\)) (.+)$' ) # not used at the moment
TIMEZONE_REGEX = compile( r'\(\w+\+\d\d:\d\d\) ' )

TYPES = {
	'AlpineSki': ActivityTypes.ski,
	'BackcountrySki': ActivityTypes.xcski_backcountry,
	'Canoeing': ActivityTypes.canoe,
	'Crossfit': ActivityTypes.crossfit,
	'EBikeRide': ActivityTypes.bike_ebike,
	'Elliptical': ActivityTypes.other,
	'Golf': ActivityTypes.golf,
	'Handcycle': ActivityTypes.bike_hand,
	'Hike': ActivityTypes.hiking,
	'IceSkate': ActivityTypes.ice_skate,
	'InlineSkate': ActivityTypes.inline_skate,
	'Kayaking': ActivityTypes.kayak,
	'Kitesurf': ActivityTypes.kitesurf,
	'NordicSki': ActivityTypes.xcski,
	'Ride': ActivityTypes.bike,
	'RockClimbing': ActivityTypes.climb,
	'RollerSki': ActivityTypes.rollski,
	'Rowing': ActivityTypes.row,
	'Run': ActivityTypes.run,
	'Sail': ActivityTypes.sail,
	'Skateboard': ActivityTypes.skateboard,
	'Snowboard': ActivityTypes.snowboard,
	'Snowshoe': ActivityTypes.snowshoe,
	'Soccer': ActivityTypes.soccer,
	'StairStepper': ActivityTypes.other,
	'StandUpPaddling': ActivityTypes.paddle_standup,
	'Surfing': ActivityTypes.surf,
	'Swim': ActivityTypes.swim,
	'Velomobile': ActivityTypes.other,
	'VirtualRide': ActivityTypes.bike_ergo,
	'VirtualRun': ActivityTypes.run_ergo,
	'Walk': ActivityTypes.walk,
	'WeightTraining': ActivityTypes.gym,
	'Wheelchair': ActivityTypes.other,
	'Windsurf': ActivityTypes.surf_wind,
	'Workout': ActivityTypes.gym,
	'Yoga': ActivityTypes.yoga,
}

CLIENT_ID_TEXT = \
'''Checking for new activities and downloading photos works by using Strava\'s REST API. To be able
to use this API you need to enter your Client ID and your Client Secret. In order to retrieve both,
you need to create your own Strava application. Head to https://www.strava.com/settings/api
and enter all necessary details. Once you created your application, the ID and the secret
will be displayed.
'''

CLIENT_CODE_TEXT = \
'''
For the next step we need to obtain the Client Code. The client code can be obtained by visiting the
authorization URL displayed below. After authorizing you will be redirected a (non-existing) URL in
your browser and the client code is part of this URL. The URL should look like this:
OAUTH_REDIRECT_URL?code=<CLIENT_CODE_IS_DISPLAYED_HERE>&scope={SCOPE}
Copy the URL from your browser.
'''

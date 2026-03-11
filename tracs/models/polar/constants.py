
from re import compile

from tracs.activity_types import ActivityTypes as Types

# resource types

POLAR_CSV_TYPE = 'text/vnd.polar+csv'
POLAR_HRV_TYPE = 'text/vnd.polar.hrv+csv'
POLAR_FLOW_TYPE = 'application/vnd.polar+json'
POLAR_FITNESS_TEST_TYPE = 'application/vnd.polar.fitness+json'
POLAR_ORTHOSTATIC_TEST_TYPE = 'application/vnd.polar.orthostatic+json'
POLAR_RRRECORDING_TYPE = 'application/vnd.polar.rrrecording+json'
POLAR_SESSION_TYPE = 'application/vnd.polar.session+json'
POLAR_EXERCISE_DATA_TYPE = 'application/vnd.polar.ped+xml'
POLAR_ZIP_GPX_TYPE = 'application/vnd.polar.gpx+zip'
POLAR_ZIP_TCX_TYPE = 'application/vnd.polar.tcx+zip'

# file globs

ACCOUNT_DATA_GLOB = 'account-data-*.json'
ACCOUNT_PROFILE_GLOB = 'account-profile-*.json'
TRAINING_SESSION_GLOB = 'training-session-*.json'

TRAINING_SESSION_REGEX = compile( r'^.*training-session-(\d{4}-\d{2}-\d{2})-(\d+)(-([a-f0-9-]+))*\.json$' )

# icon ids

# polar icon ids for identifying multipart activities: there does not seem to be any other way to identify those
ICON_ID_TRIATHLON = '003304795bc33d808ee8e6ab8bf45d1f-2015-10-20_13_45_17'  # triathlon
ICON_ID_MULTISPORT = '20951a7d8b02def8265f5231f57f4ed9-2015-10-20_13_45_40'  # multisport

# all types: https://www.polar.com/accesslink-api/#detailed-sport-info-values-in-exercise-entity
# this maps the last part of the icon URL to Polar sports types, there's no other way to find the actual type
# example: iconUrl = "https://platform.cdn.polar.com/ecosystem/sport/icon/808d0882e97375e68844ec6c5417ea33-2015-10-20_13_46_22
ICON_TYPES = {
	'003304795bc33d808ee8e6ab8bf45d1f-2015-10-20_13_45_17': Types.triathlon,
	'20951a7d8b02def8265f5231f57f4ed9-2015-10-20_13_45_40': Types.multisport,
	'22f701a2c43d7c5678140b0a3e52ddaa-2015-10-20_13_46_02': Types.rollski_classic,
	'2524f40bcd8372f0912cb213c1fc9a29-2015-10-20_13_45_29': Types.bike_road,
	'3c1103ccbeee33fa663a1dc8e0fd8a6d-2015-10-20_13_45_48': Types.xcski_classic,
	'3e8556e6cf6ed3f01e5f8af133117416-2015-10-20_13_46_00': Types.rollski_free,
	'40894732d0b606b3fd9c9c34471df222-2015-10-20_13_46_28': Types.swim_indoor,
	'49b881c0a9aec1fce68fab11f8f1b01d-2016-02-03_06_06_42': Types.gymnastics,
	'4c54b3b02bd2d8b9b3f60931776a3497-2015-10-20_13_46_07': Types.unknown,
	'4ddd474b10302e72fb53bbd69028e15b-2015-10-20_13_46_17': Types.bike_mountain,
	'561a80f6d7eef7cc328aa07fe992af8e-2015-10-20_13_46_03': Types.bike,
	'5cdfcd252814f732414d977484cef4ea-2015-10-20_13_46_11': Types.swim_outdoor,
	'808d0882e97375e68844ec6c5417ea33-2015-10-20_13_46_22': Types.run,
	'9e3fc7036226634543f971acd1a68e60-2015-11-25_10_37_05': Types.ergo,
	'a2afcae540681c227a48410d97277e2e-2015-10-20_13_45_18': Types.unknown,
	'a2e8c7a794dadb60ecbfb21239f5b981-2016-02-03_06_06_32': Types.unknown,
	'd1ce94078aec226be28f6c602e6803e1-2015-10-20_13_45_19': Types.gym,
	'e25370188b9c9b611dcafb6f0028faeb-2015-10-20_13_45_32': Types.hiking,
	'f0c9643f1cef947e5621b0b46ab06783-2015-10-20_13_46_12': Types.xcski_free,
	'f4197b0c1a4d65962b9e45226c77d4d5-2015-10-20_13_45_26': Types.swim,
}

ACCESSLINK_TYPES = {
	'AEROBICS': Types.aerobics,  # Aerobics
	'AMERICAN_FOOTBALL': Types.football,  # Football
	'AQUATICS': Types.aquatics,  # Aqua fitness
	'BACKCOUNTRY_SKIING': Types.xcski_backcountry,  # Backcountry skiing
	'BADMINTON': Types.badminton,  # Badminton
	'BALLET_DANCING': Types.ballet,  # Ballet
	'BALLROOM_DANCING': Types.dancing,  # Ballroom
	'BASEBALL': Types.baseball,  # Baseball
	'BASKETBALL': Types.basketball,  # Basketball
	'BEACH_VOLLEYBALL': Types.beach,  # Beach volley
	'BIATHLON': Types.biathlon,  # Biathlon
	'BODY_AND_MIND': Types.yoga,  # Body & Mind
	'BOOTCAMP': Types.gym,  # Bootcamp
	'BOXING': Types.boxing,  # Boxing
	'CIRCUIT_TRAINING': Types.gym,  # Circuit training
	'CORE': Types.gym,  # Core
	'CRICKET': Types.cricket,  # Cricket
	'CROSS_TRAINER': Types.gym,  # Cross-trainer
	'CROSS_COUNTRY_RUNNING': Types.run,  # Cross-country running
	'CROSS-COUNTRY_SKIING': Types.xcski,  # Skiing
	'CYCLING': Types.bike,  # Cycling
	'CLIMBING': Types.climb,  # Climbing
	'CURLING': Types.curling,  # Curling
	'DANCING': Types.dancing,  # Dancing
	'DOWNHILL_SKIING': Types.ski,  # Downhill skiing
	'DUATHLON': Types.duathlon,  # Duathlon
	'DUATHLON_CYCLING': Types.bike,  # Cycling
	'DUATHLON_RUNNING': Types.run,  # Running
	'E_BIKE': Types.bike_ebike,  # Electric biking
	'FIELD_HOCKEY': Types.hockey,  # Field hockey
	'FINNISH_BASEBALL': Types.baseball_finnish,  # Finnish baseball
	'FITNESS_DANCING': Types.dancing,  # Fitness dancing
	'FITNESS_MARTIAL_ARTS': Types.gym,  # Fitness martial arts
	'FITNESS_STEP': Types.gym,  # Step workout
	'FLOORBALL': Types.floorball,  # Floorball
	'FREE_MULTISPORT': Types.multisport,  # Multisport
	'FRISBEEGOLF': Types.golf_disc,  # Disc golf
	'FUNCTIONAL_TRAINING': Types.gym,  # Functional training
	'FUTSAL': Types.futsal,  # Futsal
	'GOLF': Types.golf,  # Golf
	'GROUP_EXERCISE': Types.other,  # Group exercise
	'GYMNASTICK': Types.gymnastics,  # Gymnastics
	'HANDBALL': Types.handball,  # Handball
	'HIIT': Types.gym,  # High-intensity interval training
	'HIKING': Types.hiking,  # Hiking
	'ICE_HOCKEY': Types.ice_hockey,  # Ice hockey
	'ICE_SKATING': Types.ice_skate,  # Ice skating
	'INDOOR_CYCLING': Types.bike_indoor,  # Indoor cycling
	'INDOOR_ROWING': Types.row_indoor,  # Indoor rowing
	'INLINE_SKATING': Types.inline_skate,  # Inline skating
	'JAZZ_DANCING': Types.dancing,  # Jazz
	'JOGGING': Types.run,  # Jogging
	'JUDO_MARTIAL_ARTS': Types.judo,  # Judo
	'KETTLEBELL': Types.gym,  # Kettlebell
	'KICKBOXING_MARTIAL_ARTS': Types.kickboxing,  # Kickboxing
	'LATIN_DANCING': Types.dancing,  # Latin
	'LES_MILLS_BARRE': Types.gym,  # LES MILLS BARRE
	'LES_MILLS_BODYATTACK': Types.gym,  # LES MILLS BODYATTACK
	'LES_MILLS_BODYBALANCE': Types.gym,  # LES MILLS BODYBALANCE
	'LES_MILLS_BODYCOMBAT': Types.gym,  # LES MILLS BODYCOMBAT
	'LES_MILLS_BODYJAM': Types.gym,  # LES MILLS BODYJAM
	'LES_MILLS_BODYPUMP': Types.gym,  # LES MILLS BODYPUMP
	'LES_MILLS_BODYSTEP': Types.gym,  # LES MILLS BODYSTEP
	'LES_MILLS_CXWORKS': Types.gym,  # LES MILLS CXWORX
	'LES_MILLS_GRIT_ATHLETIC': Types.gym,  # LES MILLS GRIT Athletic
	'LES_MILLS_GRIT_CARDIO': Types.gym,  # LES MILLS GRIT Cardio
	'LES_MILLS_GRIT_STRENGTH': Types.gym,  # LES MILLS GRIT Strength
	'LES_MILLS_RPM': Types.gym,  # LES MILLS RPM
	'LES_MILLS_SHBAM': Types.gym,  # LES MILLS SH'BAM
	'LES_MILLS_SPRINT': Types.gym,  # LES MILLS SPRINT
	'LES_MILLS_TONE': Types.gym,  # LES MILLS TONE
	'LES_MILLS_TRIP': Types.gym,  # LES MILLS TRIP
	'MOBILITY_DYNAMIC': Types.gymnastics,  # Mobility (dynamic)
	'MOBILITY_STATIC': Types.gymnastics,  # Mobility (static)
	'MODERN_DANCING': Types.dancing,  # Modern
	'MOTORSPORTS_CAR_RACING': Types.drive_road,  # Car racing
	'MOTORSPORTS_ENDURO': Types.drive_enduro,  # Enduro
	'MOTORSPORTS_HARD_ENDURO': Types.drive_enduro,  # Hard Enduro
	'MOTORSPORTS_MOTOCROSS': Types.drive_cross,  # Motocorss
	'MOTORSPORTS_ROADRACING': Types.drive_road,  # Road racing
	'MOTORSPORTS_SNOCROSS': Types.drive_snow,  # Snocross
	'MOUNTAIN_BIKING': Types.bike_mountain,  # Mountain biking
	'NORDIC_WALKING': Types.walk_nordic,  # Nordic walking
	'OFFROADDUATHLON': Types.duathlon,  # Off-road duathlon
	'OFFROADDUATHLON_CYCLING': Types.bike,  # Mountain biking
	'OFFROADDUATHLON_RUNNING': Types.run,  # Trail running
	'OFFROADTRIATHLON': Types.triathlon,  # Off-road triathlon
	'OFFROADTRIATHLON_CYCLING': Types.bike,  # Mountain biking
	'OFFROADTRIATHLON_RUNNING': Types.run,  # Trail running
	'OFFROADTRIATHLON_SWIMMING': Types.swim_outdoor,  # Open water swimming
	'OPEN_WATER_SWIMMING': Types.swim_outdoor,  # Open water swimming
	'ORIENTEERING': Types.orienteering,  # Orienteering
	'ORIENTEERING_MTB': Types.orienteering_bike,  # Mountain bike orienteering
	'ORIENTEERING_SKI': Types.orienteering_ski,  # Ski orienteering
	'OTHER_INDOOR': Types.other_indoor,  # Other indoor
	'OTHER_OUTDOOR': Types.other_outdoor,  # Other outdoor
	'PADEL': Types.paddle,  # Padel racing
	'PARASPORTS_WHEELCHAIR': Types.wheelchair,  # Wheelchair racing
	'PILATES': Types.pilates,  # Pilates
	'POOL_SWIMMING': Types.swim_indoor,  # Pool swimming
	'RIDING': Types.ride,  # Riding
	'ROAD_BIKING': Types.bike_road,  # Road cycling
	'ROAD_RUNNING': Types.run,  # Road running
	'ROLLER_BLADING': Types.roller_blade,  # Roller skating
	'ROLLER_SKIING_CLASSIC': Types.rollski_classic,  # Classic roller skiing
	'ROLLER_SKIING_FREESTYLE': Types.rollski_free,  # Freestyle roller skiing
	'ROWING': Types.row,  # Rowing
	'RUGBY': Types.rugby,  # Rugby
	'RUNNING': Types.run,  # Running
	'SHOW_DANCING': Types.dancing,  # Show
	'SKATEBOARDING': Types.skateboard,  # Skateboarding
	'SKATING': Types.inline_skate,  # Skating
	'SNOWBOARDING': Types.snowboard,  # Snowboarding
	'SNOWSHOE_TREKKING': Types.snowshoe,  # Snowshoe trekking
	'SOCCER': Types.soccer,  # Soccer
	'SPINNING': Types.spinning,  # Spinning
	'SUP': Types.paddle_standup,  # SUP
	'SQUASH': Types.squash,  # Squash
	'STREET_DANCING': Types.dancing,  # Street
	'STRENGTH_TRAINING': Types.gym,  # Strength training
	'STRETCHING': Types.gymnastics,  # Stretching
	'SWIMMING': Types.swim,  # Swimming
	'TABLE_TENNIS': Types.table_tennis,  # Table tennis
	'TAEKWONDO_MARTIAL_ARTS': Types.taekwondo,  # Taekwondo
	'TELEMARK_SKIING': Types.telemark,  # Telemark skiing
	'TENNIS': Types.tennis,  # Tennis
	'TRACK_AND_FIELD_RUNNING': Types.run,  # Track&field running
	'TRAIL_RUNNING': Types.run,  # Trail running
	'TREADMILL_RUNNING': Types.run_ergo,  # Treadmill running
	'TRIATHLON': Types.triathlon,  # Triathlon
	'TRIATHLON_CYCLING': Types.bike,  # Cycling
	'TRIATHLON_RUNNING': Types.run,  # Running
	'TRIATHLON_SWIMMING': Types.swim_outdoor,  # Open water swimming
	'TROTTING': Types.trotting,  # Trotting
	'ULTRARUNNING_RUNNING': Types.run,  # Ultra running
	'VERTICALSPORTS_WALLCLIMBING': Types.climb,  # Climbing (indoor)
	'VERTICALSPORTS_OUTCLIMBING': Types.climb,  # Climbing (outdoor)
	'VOLLEYBALL': Types.volleyball,  # Volleyball
	'WALKING': Types.walk,  # Walking
	'WATER_EXERCISE': Types.aquatics,  # Water sports
	'WATER_RUNNING': Types.aquatics,  # Water running
	'WATERSPORTS_CANOEING': Types.canoe,  # Canoeing
	'WATERSPORTS_KAYAKING': Types.kayak,  # Kayaking
	'WATERSPORTS_KITESURFING': Types.kitesurf,  # Kitesurfing
	'WATERSPORTS_SAILING': Types.sail,  # Sailing
	'WATERSPORTS_SURFING': Types.surf,  # Surfing
	'WATERSPORTS_WAKEBOARDING': Types.wakeboard,  # Wakeboarding
	'WATERSPORTS_WATERSKI': Types.waterski,  # Water skiing
	'WATERSPORTS_WINDSURFING': Types.surf_wind,  # Windsurfing
	'XC_SKIING_CLASSIC': Types.xcski_classic,  # Classic XC skiing
	'XC_SKIING_FREESTYLE': Types.xcski_free,  # Freestyle XC skiing
	'YOGA': Types.yoga,  # Yoga
}

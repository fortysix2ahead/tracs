
from re import compile

TAKEOUTS_DIRNAME = 'takeouts'
ACTIVITY_FILE = 'account_activity_3.csv'
INFO_FILE = 'account_info.csv'

SERVICE_NAME = 'waze'
DISPLAY_NAME = 'Waze'

WAZE_TYPE = 'text/vnd.waze+txt'
WAZE_ACCOUNT_ACTIVITY_TYPE = 'text/vnd.waze.activity+csv'
WAZE_ACCOUNT_INFO_TYPE = 'text/vnd.waze.info+csv'
WAZE_TAKEOUT_TYPE = WAZE_ACCOUNT_ACTIVITY_TYPE # for backward compatibility

DEFAULT_FIELD_SIZE_LIMIT = 131072

# predefined regular expressions

DATE = compile( r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (GMT|UTC)$' )
COORDS_1 = compile( r'^\(\d+\.\d+ \d+\.\d+\)$' )
COORDS_2 = compile( r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC\(\d+\.\d+ \d+\.\d+\)$' )
COORDS_3 = compile( r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+00\(\d+\.\d+ \d+\.\d+\)$' )
COORDS_LIST_1 = compile( r'^\([\d. ]+\)(\|\([\d. ]+\))*$' )
COORDS_LIST_2 = compile( r'^[\d-]+ [\d:]+ UTC\([\d. ]+\)(\|[\d-]+ [\d:]+ UTC\([\d. ]+\))*' )

CURLY_BRACES = compile( r'\{.+?}' )

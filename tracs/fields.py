from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
from enum import Enum

filter_types = {
	'ascent'     : float,
	'calories'   : float,
	'classifier' : str,
	'date'       : date,
	'datetime'   : datetime,
	'descent'    : float,
	'description': str,
	'distance'   : float,
	'duration'   : time,
	'heartrate'  : float,
	'id'         : int,
	'name'       : str,
	'raw_id'     : int,
	'service'    : str,
	'source'     : str,
	'speed'      : float,
	'tags'       : list[str],
	'time'       : time,
	'type'       : Enum,
	'uid'        : str,
	'uids'       : list[str],
}

field_types = {
	'ascent'     : float,
	'calories'   : float,
	'classifier' : str,
	'descent'    : float,
	'description': str,
	'distance'   : float,
	'duration'   : time,
	'heartrate'  : float,
	'id'         : int,
	'localtime'  : datetime,
	'name'       : str,
	'raw_id'     : int,
	'speed'      : float,
	'tags'       : list[str],
	'time'       : datetime,
	'type'       : Enum,
	'uid'        : str,
	'uids'       : list[str],
}

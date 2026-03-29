from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import zip_longest
from logging import getLogger
from pathlib import Path
from re import match
from sys import exit as sysexit
from time import time
from typing import ClassVar, Dict, List, Optional, Tuple, Union
from webbrowser import open as open_url

from dateutil.parser import parse as dtparse
from dateutil.tz import UTC
from dynaconf.utils.boxing import DynaBox
from fs.base import FS
from fs.path import dirname
from lxml.etree import tostring
from requests import get as rqget
from rich.prompt import Prompt
from stravalib.client import Client

from tracs.activity import Activities, Activity
from tracs.constants import APPNAME, CFG_CLASSIFIER
from tracs.pluginmgr import resourcetype, service, setup
from tracs.plugins.gpx import GPX_TYPE
from tracs.plugins.image import JPEG_TYPE
from tracs.plugins.json import JSONHandler
from tracs.plugins.strava.constants import CLIENT_CODE_TEXT, CLIENT_ID_TEXT, FETCH_PAGE_SIZE, OAUTH_REDIRECT_URL, PHOTO_SIZE, SCOPE, STRAVA_TYPE
from tracs.plugins.strava.io import StravaHandler
from tracs.plugins.tcx import TCX_TYPE
from tracs.resources import Resource, ResourceType
from tracs.service import Service
from tracs.streams import Point, Stream
from tracs.ui import CONSOLE as cs
from tracs.uid import uid

log = getLogger( __name__ )

SERVICE_NAME = 'strava'
DISPLAY_NAME = 'Strava'

@resourcetype
def strava_resource_type() -> ResourceType:
	return ResourceType( name=STRAVA_TYPE, summary=True )

@service
class Strava( Service ):

	SERVICE_NAME: ClassVar[str] = SERVICE_NAME

	def __init__( self, **kwargs ):
		super().__init__( **kwargs )

		self._client = Client()
		self._session = None
		self._oauth_session = None

		self.importer: StravaHandler = StravaHandler()
		self.json_handler: JSONHandler = JSONHandler()

	@property
	def activities_url( self ) -> str:
		return f'{self.base_url}/activities'

	def url_events_year( self, year, page: int ) -> str:
		after = int( datetime( year, 1, 1, tzinfo=UTC ).timestamp() )
		before = int( datetime( year + 1, 1, 1, tzinfo=UTC ).timestamp() )
		per_page = FETCH_PAGE_SIZE # we might make this configurable later ...
		return f'{self.base_url}/api/v3/athlete/activities?before={before}&after={after}&page={page}&per_page={per_page}'

	def all_events_url( self, page: int ) -> str:
		after = int( datetime( 1970, 1, 1, tzinfo=UTC ).timestamp() )
		before = int( datetime( datetime.now( UTC ).year + 1, 1, 1, tzinfo=UTC ).timestamp() )
		per_page = FETCH_PAGE_SIZE  # we might make this configurable later ...
		return f'{self.base_url}/api/v3/athlete/activities?before={before}&after={after}&page={page}&per_page={per_page}'

	def url_for_id( self, local_id: Union[int, str] ) -> Optional[str]:
		return f'{self.activities_url}/{local_id}'

	def url_for_resource_type( self, local_id: Union[int, str], type: str ) -> Optional[str]:
		if type == GPX_TYPE:
			return f'{self._activities_url}/{local_id}/export_gpx'
		elif type == TCX_TYPE:
			return f'{self._activities_url}/{local_id}/export_original'

	def _link_path( self, activity: Activity, ext: str ) -> Path or None:
		#		if activity.id:
		utc = activity.utctime
		parent = Path( self._lib_dir, utc.strftime( '%Y/%m/%d' ) )
		#			a = self.db.get_activity( activity )
		#			if a and a.name:
		#				return Path( parent, f'{utc.strftime( "%H%M%S" )} - {a.name}.strava.{ext}' )  # fully qualified path
		#			else:
		return Path( parent, f'{utc.strftime( "%H%M%S" )}.{self.name}.{ext}' )  # fully qualified path

	# service methods

	def supports_remote_import( self ) -> bool:
		return True

	def login( self ):
		# check if access/refresh tokens are available
		if not self._state.access_token and not self._state.refresh_token:
			log.error( f"application setup not complete for {SERVICE_NAME}, consider running {APPNAME} setup --strava" )
			sysexit( -1 )

		self._client = Client( access_token=self._state.access_token )

		if time() > self.state_value( 'expires_at' ):
			log.debug( f"access token has expired, attempting to fetch new one" )
			client_id = self._cfg.client_id
			client_secret = self._cfg.client_secret
			refresh_token = self._state.refresh_token
			refresh_response = self._client.refresh_access_token( client_id=client_id, client_secret=client_secret, refresh_token=refresh_token )

			self._state['access_token'] = refresh_response.get( 'access_token' )
			self._state['refresh_token'] = refresh_response.get( 'refresh_token' )
			self._state['expires_at'] = refresh_response.get( 'expires_at' )

		# todo: how to detect unsuccessful login?
		return True

	def import_from_remote( self, dest_fs: FS, **kwargs ) -> Activities:
		after = kwargs.get( 'range_from' )
		before = kwargs.get( 'range_to' )
		first_year = self._ctx.config['import'].first_year

		if after is None or before is None:
			after, before = datetime( first_year, 1, 1 ), datetime.now( UTC ) + timedelta( days = 1 )

		imported = Activities()

		if self.login():
			summary_ids = [ sa.id for sa in self._client.get_activities( after=after, before=before ) ]
			summary_uids = [ uid( f'{self._cfg.get( CFG_CLASSIFIER ) or self.name}:{id}' ) for id in summary_ids ]

			# filter existing
			summary_uids = [ u for u in summary_uids if self.ctx.force or not self.db.get_by_uid( u ) ]

			for u in summary_uids:
				path = self.db_path_for( u.local_id, f'{u.local_id}.json' )

				# fetch detailed activity
				summary = self._summary( u.local_id )

				# streams

				# available streams:
				# time, latlng, distance, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth
				# gpx contains lat/lon, elevation, time + time in metadata
				# tcx contains TotalTimeSeconds, DistanceMeters, MaximumSpeed, Calories
				# track contains Time, LatitudeDegrees, LongitudeDegrees, AltitudeMeters, DistanceMeters, SensorState
				streams = self._client.get_activity_streams( u.local_id, types=[ 'time', 'latlng', 'distance', 'altitude', 'velocity_smooth', 'heartrate' ] )
				stream = to_stream( streams, summary.data.start_date )

				# TCX Recording
				tcx = self._tcx( stream, summary.raw )

				# GPX
				gpx = self._gpx( stream, summary.raw )

				# Photos
				photos = self._photos( summary.raw )

				# write resources
				resources = [ r for r in [summary, gpx, tcx, *photos] if r is not None ]
				for r in resources:
					r.unload_to( dest_fs, r.path )
					log.debug( f'wrote resource to {dest_fs}/{r.path}' )

				# append resources
				activity = self.importer.load_as_activity( resource=summary, fs=dest_fs, attach=False )
				activity.resources.add_all( *resources )
				# todo: check why unload does not here ...
				for r in activity.resources:
					r.unload()
				# todo_end
				imported.append( activity )

		return imported

	def _summary( self, id: int ) -> Resource:
		da = self._client.get_activity( id, include_all_efforts=True )  # get detailed data for activity
		dump = da.model_dump_json( exclude_unset=True, exclude_defaults=True, exclude_none=True )
		data = self.json_handler.load_raw( dump )  # todo: check if there's a better way of getting a sorted json
		sorted_dump = self.json_handler.save_raw( data )

		return Resource(
			content=sorted_dump,
			raw=data,
			data=da,
			name=f'{id}.json',
			path=self.db_path_for( id, f'{id}.json' ),
			type=STRAVA_TYPE,
			source=self.url_for_id( da.id ),
		)

	def _gpx( self, stream, raw: Dict ) -> Optional[Resource]:
		if any( p.lat for p in stream.points ):
			return Resource(
				name=f'{raw.get( "id" )}.tcx',
				path=self.db_path_for( raw.get( 'id' ), f'{raw.get( "id" )}.gpx' ),
				type=GPX_TYPE,
				# track_type = '1' # todo: don't know what GPX type means, strava uses integer numbers
				text=stream.as_gpx( track_name=raw.get( 'name' ) ).to_xml( prettyprint=True )
			)
		else:
			return None

	def _tcx( self, stream, raw: Dict ) -> Resource:
		tcx = stream.as_tcx(
			average_heart_rate_bpm=raw.get( 'average_heartrate' ),
			calories=round( raw.get( 'calories' ) ),
			distance_meters=raw.get( 'distance' ),
			id=f'{raw.get( "start_date_local" )}Z',
			intensity='Active',  # todo: don't know where to get this from
			maximum_heart_rate_bpm=raw.get( 'max_heartrate' ),
			maximum_speed=raw.get( 'max_speed' ),
			start_date=dtparse( sd ) if type( sd := raw.get( 'start_date' ) ) is str else sd,
			# trigger_method = 'Distance', # todo: this is not correct
			total_time_seconds=round( raw.get( 'elapsed_time' ) ),
		)
		return Resource(
			name=f'{raw.get( "id" )}.tcx',
			path=self.db_path_for( raw.get( 'id' ), f'{raw.get( "id" )}.tcx' ),
			text=tostring( tcx.as_xml(), pretty_print=True ).decode( 'UTF-8' ),
			type=TCX_TYPE,
		)

	def _photos( self, raw: Dict ) -> List[Resource]:
		photos = []
		if raw.get( 'photos' ).get( 'count' ) > 0:
			for photo, index in zip( self._client.get_activity_photos( raw.get( 'id' ), size=PHOTO_SIZE ), range( 1, 100 ) ):
				photo_url = photo.urls.get( str( PHOTO_SIZE ) )
				if photo_url and (response := rqget( photo_url )) and response.status_code == 200:
					photos.append(
						Resource(
							content=response.content,
							name=f'{raw.get( "id" )}.{index}.jpg',
							path=self.db_path_for( raw.get( 'id' ), f'{raw.get( "id" )}.{index}.jpg' ),
							type=JPEG_TYPE,
						)
					)

		return photos

	@property
	def logged_in( self ) -> bool:
		return True if self._session and self._oauth_session else False

	def setup( self ) -> Tuple[DynaBox, DynaBox]:
		cfg, state = DynaBox(), DynaBox()
		client = Client()

		cs.print( CLIENT_ID_TEXT, width=120 )

		client_id = Prompt.ask( 'Enter your Client ID', default=self._cfg.get( 'client_id' ) )
		client_secret = Prompt.ask( 'Enter your Client Secret', default=self._cfg.get( 'client_secret' ) )

		authorize_url = client.authorization_url( client_id=client_id, redirect_uri=OAUTH_REDIRECT_URL, scope=SCOPE )

		cs.print( CLIENT_CODE_TEXT )
		cs.print( f'Authorization URL: {authorize_url}' )
		cs.print()
		callback_url = Prompt.ask( f'Paste the URL from your browser' )

		state_, client_code, scope = match( '^.+\?state=(.*)&code=(\w+)&scope=(.+)$', callback_url ).groups()

		try:
			token_response = client.exchange_code_for_token( client_id=client_id, client_secret=client_secret, code=client_code )

			# state.state = state_ # not needed
			state.client_code = client_code
			state.scope = scope

			state.access_token = token_response.get( 'access_token' )
			state.refresh_token = token_response.get( 'refresh_token' )
			state.expires_at = token_response.get( 'expires_at' )

			log.debug( f"fetched access and refresh token for athlete {client.get_athlete().id}, expiring at {state.expires_at}" )

			return cfg, state

		except RuntimeError as rte:
			cs.print( f'Error: authorization not granted.' )
			cs.print( rte )

		return cfg, state

class StravaSetupServer( BaseHTTPRequestHandler ):

	client_code = None

	def do_GET(self):
		if m := match( '^.+code=([\da-f]+).*$', self.path ):
			StravaSetupServer.client_code = m[1]
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(bytes("<html><head><title></title></head>", "utf-8"))
		if m[1]:
			self.wfile.write(bytes("<body><p>Client code successfully detected, you can close this window.</p></body>", "utf-8"))
		else:
			self.wfile.write( bytes( "<body><p>Error: unable to detect client code in URL.</p></body>", "utf-8" ) )
		self.wfile.write(bytes("</html>", "utf-8"))
		raise KeyboardInterrupt

def fetch_client_code( authorize_url ):
	open_url( authorize_url )
	webServer = HTTPServer( ('localhost', 40004), StravaSetupServer )

	try:
		webServer.serve_forever()
	except KeyboardInterrupt:
		pass

	client_code = StravaSetupServer.client_code
	webServer.server_close()

	return client_code

# helper

class EmptyStream:

	@property
	def data( self ) -> List:
		return []

EMPTY = EmptyStream()

def to_stream( streams: Dict, start_date: datetime ) -> Stream:
	stream_iterator = zip_longest(
		streams.get( 'time', EMPTY ).data,
		streams.get( 'latlng', EMPTY ).data,
		streams.get( 'distance', EMPTY ).data,
		streams.get( 'altitude', EMPTY ).data,
		streams.get( 'velocity_smooth', EMPTY ).data,
		streams.get( 'heartrate', EMPTY ).data,
		fillvalue=None
	)
	points = [ Point( distance=d, alt=a, speed=vs, hr=hr, start=start_date, seconds=t, latlng=ll ) for t, ll, d, a, vs, hr in stream_iterator ]
	return Stream( points=points )

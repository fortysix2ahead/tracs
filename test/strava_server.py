
from threading import Thread
from typing import Optional

from bottle import Bottle
from bottle import static_file

from pytest import fixture

from tracs.plugins.strava import Strava
from .helpers import get_file_path

TEST_HOST = 'localhost'
TEST_PORT = 40081
TEST_BASE_URL = f'http://{TEST_HOST}:{TEST_PORT}'
LIVE_BASE_URL = 'https://www.strava.com'

server = Bottle()
server_function = server.run
server_args = {
	'host' : TEST_HOST,
	'port' : TEST_PORT,
	'debug': True,
}
server_thread = Thread(target=server_function, kwargs=server_args, daemon=True)

@server.get('/')
def root():
	return static_file('weblogin.html', root=get_file_path('templates/strava'), mimetype='text/html')

@server.get('/login')
def login():
	return static_file('session.html', root=get_file_path('templates/strava'), mimetype='text/html')

@server.post('/session')
def login():
	return static_file('session.html', root=get_file_path('templates/strava'), mimetype='text/html')

# fixture starting a background server

@fixture
def strava_server() -> Bottle:
	if not server_thread.is_alive():
		server_thread.start()
	return server

@fixture
def strava_service( request ) -> Optional[Strava]:
	if marker := request.node.get_closest_marker( 'base_url' ):
		strava = Strava()
		strava.base_url = marker.args[0]
		return strava
	return None

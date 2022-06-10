
from threading import Thread

from bottle import Bottle
from bottle import static_file

from .helpers import get_file_path

TEST_HOST = 'localhost'
TEST_PORT = 40081
TEST_BASE_URL = f'http://{TEST_HOST}:{TEST_PORT}'
LIVE_BASE_URL = 'https://www.strava.com'

strava_server = Bottle()
strava_server_function = strava_server.run
strava_server_args = {
	'host' : TEST_HOST,
	'port' : TEST_PORT,
	'debug': True,
}
strava_server_thread = Thread(target=strava_server_function, kwargs=strava_server_args, daemon=True)

@strava_server.get('/')
def root():
	return static_file('weblogin.html', root=get_file_path('templates/strava'), mimetype='text/html')

@strava_server.get('/login')
def login():
	return static_file('session.html', root=get_file_path('templates/strava'), mimetype='text/html')

@strava_server.post('/session')
def login():
	return static_file('session.html', root=get_file_path('templates/strava'), mimetype='text/html')

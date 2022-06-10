
from threading import Thread

from bottle import Bottle
from bottle import static_file

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

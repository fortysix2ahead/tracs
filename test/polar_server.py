from pathlib import Path
from threading import Thread

from bottle import Bottle
from bottle import request
from bottle import static_file

from pytest import fixture

from tracs.config import ApplicationConfig as cfg
from tracs.config import GlobalConfig as gc
from tracs.config import KEY_PLUGINS
from tracs.plugins.polar import Polar
from .helpers import get_file_path
from .helpers import var_run_path

TEST_HOST = 'localhost'
TEST_PORT = 40080
TEST_BASE_URL = f'http://{TEST_HOST}:{TEST_PORT}'

LIVE_BASE_URL = 'https://flow.polar.com'

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
	return static_file('index.html', root=get_file_path('templates/polar'), mimetype='text/html')


@server.get('/ajaxLogin')
def ajax_login():
	return static_file('ajaxlogin.html', root=get_file_path('templates/polar'), mimetype='text/html')


@server.post('/login')
def login():
	return static_file('login.html', root=get_file_path('templates/polar'), mimetype='text/html')


@server.get('/training/getCalendarEvents')
def events():
	start, end = request.params.get('start'), request.params.get('end')
	root_path = get_file_path('templates/polar')
	filename = f"{start.rsplit('.', 1)[1]}.json"
	path = Path(root_path, filename)
	if path.exists():
		return static_file(filename=filename, root=root_path, mimetype='text/json')
	else:
		return '[]'


@server.get('/api/export/training/csv/<id:int>')
def download_csv(id):
	return static_file('empty.csv', root=get_file_path('templates/polar'))


@server.get('/api/export/training/rr/csv/<id:int>')
def download_csv(id):
	return static_file('empty.hrv', root=get_file_path('templates/polar'))


@server.get('/api/export/training/gpx/<id:int>')
def download_gpx(id):
	return static_file('empty.gpx', root=get_file_path('templates/polar'))


@server.get('/api/export/training/tcx/<id:int>')
def download_gpx(id):
	return static_file('empty.tcx', root=get_file_path('templates/polar'))


# fixture starting a background server

@fixture
def polar_server() -> Bottle:
	if not server_thread.is_alive():
		server_thread.start()
	return server

@fixture
def polar_test_service() -> Polar:
	polar = Polar()
	polar.base_url = TEST_BASE_URL

	cfg[KEY_PLUGINS]['polar']['username'] = 'sample user'
	cfg[KEY_PLUGINS]['polar']['password'] = 'sample password'

	return polar

@fixture
def polar_live_service() -> Polar:
	polar = Polar()
	polar.base_url = LIVE_BASE_URL
	return polar

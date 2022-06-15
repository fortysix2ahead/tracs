from pathlib import Path
from threading import Thread

from bottle import Bottle
from bottle import request
from bottle import static_file

from .helpers import get_file_path

TEST_HOST = 'localhost'
TEST_PORT = 40080
TEST_BASE_URL = f'http://{TEST_HOST}:{TEST_PORT}'

LIVE_BASE_URL = 'https://flow.polar.com'

polar_server = Bottle()
polar_server_function = polar_server.run
polar_server_args = {
	'host' : TEST_HOST,
	'port' : TEST_PORT,
	'debug': True,
}
polar_server_thread = Thread(target=polar_server_function, kwargs=polar_server_args, daemon=True)

@polar_server.get('/')
def root():
	return static_file('index.html', root=get_file_path('templates/polar'), mimetype='text/html')

@polar_server.get('/ajaxLogin')
def ajax_login():
	return static_file('ajaxlogin.html', root=get_file_path('templates/polar'), mimetype='text/html')

@polar_server.post('/login')
def login():
	return static_file('login.html', root=get_file_path('templates/polar'), mimetype='text/html')

@polar_server.get('/training/getCalendarEvents')
def events():
	return static_file('all.json', root=get_file_path('templates/polar'), mimetype='text/html')

@polar_server.get('/api/export/training/csv/<id:int>')
def download_csv(id):
	return static_file('empty.csv', root=get_file_path('templates/polar'))

@polar_server.get('/api/export/training/rr/csv/<id:int>')
def download_csv(id):
	return static_file('empty.hrv', root=get_file_path('templates/polar'))

@polar_server.get('/api/export/training/gpx/<id:int>')
def download_gpx(id):
	return static_file('empty.gpx', root=get_file_path('templates/polar'))

@polar_server.get('/api/export/training/tcx/<id:int>')
def download_gpx(id):
	return static_file('empty.tcx', root=get_file_path('templates/polar'))

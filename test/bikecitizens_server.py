
from threading import Thread

from bottle import Bottle
from bottle import static_file

from .helpers import get_file_path

TEST_HOST = 'localhost'
TEST_PORT = 40082
TEST_BASE_URL = f'http://{TEST_HOST}:{TEST_PORT}'
TEST_API_URL = f'http://{TEST_HOST}:{TEST_PORT}'

bikecitizens_server = Bottle()
bikecitizens_server_function = bikecitizens_server.run
bikecitizens_server_args = {
	'host' : TEST_HOST,
	'port' : TEST_PORT,
	'debug': True,
}
bikecitizens_server_thread = Thread(target=bikecitizens_server_function, kwargs=bikecitizens_server_args, daemon=True)

@bikecitizens_server.get('/')
def root():
	return static_file('index.html', root=get_file_path('templates/bikecitizens'), mimetype='text/html')


from threading import Thread

from bottle import Bottle
from bottle import static_file

from pytest import fixture

from .helpers import get_file_path

TEST_HOST = 'localhost'
TEST_PORT = 40080

server = Bottle()
server_function = server.run
server_args = {
    'host': TEST_HOST,
    'port': TEST_PORT,
    'debug': True,
}
server_thread = Thread(target=server_function, kwargs=server_args, daemon=True)

@server.get('/')
def root():
    return static_file( 'index.html', root=get_file_path( 'templates/polar' ), mimetype='text/html' )

@server.get('/ajaxLogin')
def ajax_login():
    return static_file( 'ajaxlogin.html', root=get_file_path( 'templates/polar' ), mimetype='text/html' )

@server.post('/login')
def login():
    return '<p>Success</p>'

# fixture starting a background server

@fixture
def polar_server() -> Bottle:
    if not server_thread.is_alive():
        server_thread.start()
    return server

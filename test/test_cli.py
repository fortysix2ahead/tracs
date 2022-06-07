from pathlib import Path
from shutil import rmtree
from typing import List
from typing import Tuple

from click import echo
from click import secho
from click.testing import CliRunner
from click.testing import Result

from gtrac.cli import cli
from gtrac.config import GlobalConfig as gc

from .helpers import prepare_environment

cfg_path: Path = None
lib_path: Path = None
live_cfg_path: Path = None
live_lib_path: Path = None

main_options = []
main_debug_options = []
live_options = []

cmd_config = 'config'
cmd_fetch_polar = 'fetch -r polar'
cmd_fetch_strava = 'fetch -r strava'
cmd_list_thisyear = 'list date:thisyear'
cmd_inspect_1 = 'inspect 1'
cmd_show_1 = 'show 1'
cmd_show_86 = 'show 86'
cmd_version = 'version'

# setup / teardown ========================================

def setup_module( module ):
	global cfg_path, lib_path
	global live_cfg_path, live_lib_path
	global main_options, main_debug_options, live_options

	cfg_path, lib_path = prepare_environment( 'live', 'None', 'empty' )
	live_cfg_path, live_live_path = prepare_environment( 'live', 'None', 'live-220325' )

	main_options = ['-c', cfg_path.as_posix(), '-l', lib_path.as_posix()]
	main_debug_options = ['-d', '-c', cfg_path.as_posix(), '-l', lib_path.as_posix()]
	live_options = ['-c', live_cfg_path.as_posix(), '-l', live_live_path.as_posix()]

def teardown_module( module ):
	global cfg_path, lib_path
	#rmtree( cfg_path )

def setup_function( function ):
	secho( f'setup_function {function.__name__}' )

def teardown_function( function ):
	secho( f'teardown_function {function.__name__}' )

def test_fetch():
	runner, result, stdout = invoke( cmd_fetch_polar, log=True )
	runner, result, stdout = invoke( cmd_fetch_strava, log=True )

def test_list():
	runner, result, stdout = invoke( cmd_list_thisyear, live_options, True )

def test_inspect():
	invoke( cmd_inspect_1, live_options, True )

def test_list_show():
	runner, result, stdout = invoke( cmd_list_thisyear, live_options, True )
	runner, result, stdout = invoke( cmd_show_1, live_options, True )
	runner, result, stdout = invoke( cmd_show_86, live_options, True )

def test_config():
	runner, result, stdout = invoke( cmd_config )
	assert result.exit_code == 0

def test_version():
	runner, result, stdout = invoke( cmd_version )

	assert result.exit_code == 0
	assert '0.1.0' in result.stdout

# helpers

def invoke( cmd: str or List[str], options: List = None, log=False ) -> Tuple[CliRunner, Result, List[str]]:
	runner = CliRunner()
	if type( cmd ) is str:
		if options:
			full_cmd = list( options )
		else:
			full_cmd = list( main_options )
		full_cmd.extend( _split( cmd ) )
	else:
		full_cmd = cmd

	echo( f'running command: {full_cmd}' )

	result = runner.invoke( cli, full_cmd )
	stdout = result.stdout.splitlines()
	#stderr = result.stderr.splitlines()

	if log:
		for line in stdout:
			print( line )
	#	for line in stderr:
	#		print( line )

	# assert result.exit_code == 0

	return runner, result, stdout

def _split( cmd: str ) -> List[str]:
	return cmd.split( " " )

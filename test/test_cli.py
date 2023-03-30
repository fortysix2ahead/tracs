
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

from click import echo
from click.testing import CliRunner
from click.testing import Result
from pytest import mark

from tracs.cli import cli
from tracs.config import ApplicationContext
from .helpers import skip_live

cfg_path: Optional[Path] = None
lib_path: Optional[Path] = None
live_cfg_path: Optional[Path] = None
live_lib_path: Optional[Path] = None

main_options = []
main_debug_options = []
live_options = []

cmd_config = 'config'
cmd_fetch_polar = 'fetch polar'
cmd_fetch_strava = 'fetch strava'
cmd_fields = 'fields'
cmd_list_thisyear = 'list date:thisyear'
cmd_inspect_1 = 'inspect 1'
cmd_list = 'list'
cmd_show_1 = 'show 1'
cmd_show_86 = 'show 86'
cmd_version = 'version'

# setup / teardown ========================================

def _setup_module( module ):
	pass

def _teardown_module( module ):
	pass

def setup_function( function ):
	pass

def teardown_function( function ):
	pass

# live tests

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
def test_polar( ctx ):
	runner, result, stdout = invoke( ctx, cmd = cmd_fetch_polar, log = True )
	runner, result, stdout = invoke( ctx, cmd = cmd_list, log = True )
	runner, result, stdout = invoke( ctx, cmd = cmd_show_1, log = True )
	runner, result, stdout = invoke( ctx, cmd = cmd_inspect_1, log = True )

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
def test_strava( ctx ):
	runner, result, stdout = invoke( ctx, cmd = cmd_fetch_strava, log = False )
	runner, result, stdout = invoke( ctx, cmd = cmd_list, log = True )
	runner, result, stdout = invoke( ctx, cmd = cmd_show_1, log = True )
	runner, result, stdout = invoke( ctx, cmd = cmd_inspect_1, log = True )

@skip_live
@mark.context( library='empty', config='live', cleanup=True )
def test_config( ctx ):
	runner, result, stdout = invoke( ctx, cmd=cmd_config, log=True )
	assert result.exit_code == 0

@skip_live
@mark.context( library='empty', config='live', cleanup=False )
def test_version( ctx ):
	runner, result, stdout = invoke( ctx, cmd = cmd_version )
	assert result.exit_code == 0 and '0.1.0' in result.stdout

# helpers

def invoke( ctx: ApplicationContext, options: str = None, cmd: str = None, cmd_options: str = None, log = False ) -> Tuple[CliRunner, Result, List[str]]:
	runner = CliRunner()

	full_cmd = []
	full_cmd.extend( options.split( ' ' ) if options else [] )
	full_cmd.extend( [ '-c', str( ctx.config_dir ) ] )
	full_cmd.extend( cmd.split( ' ' ) if cmd else [] )
	full_cmd.extend( cmd_options.split( ' ' ) if cmd_options else [] )

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

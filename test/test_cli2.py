
from typing import List
from typing import Tuple

from click.testing import CliRunner
from pytest import mark

from tracs.cli import cli
from tracs.config import ApplicationContext

cmd_list = 'list'
cmd_version = 'version'

# no command

@mark.context( library='default', config='default', takeout='default', cleanup=True )
def test_nocommand( ctx ):
	code, out, err = invoke2( ctx, '' )
	assert code == 0 and 'Usage' in out[0]

# list

@mark.context( library='default', config='default', takeout='default', cleanup=False )
def test_list( ctx ):
	code, out, err = invoke2( ctx, cmd_list )
	assert code == 0 and len( out ) > 20 and 'Berlin' in out[6] # should be a table with more than 20 lines

# version

@mark.context( library='default', config='default', takeout='default', cleanup=True )
def test_version( ctx ):
	code, out, err = invoke2( ctx, cmd_version )
	assert code == 0 and '0.1.0' == out[0]

def invoke2( ctx: ApplicationContext, cmdline: str ) -> Tuple[int, List[str], List[str]]:
	runner = CliRunner( mix_stderr=False )
	cmdline = f'-c {ctx.config_dir} {cmdline}'
	result = runner.invoke( cli, cmdline )
	return result.exit_code, result.stdout.splitlines(), result.stderr.splitlines()

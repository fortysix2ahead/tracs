
from dataclasses import dataclass
from dataclasses import field
from typing import List

from click.testing import CliRunner
from pytest import mark

from tracs.cli import cli
from tracs.config import ApplicationContext

@dataclass
class Invocation:

	code: int = field()
	out: List[str] = field()
	err: List[str] = field()

	# certain line equals tern

	def assert_err_line_is( self, term: str, line_no: int ):
		assert len( self.err ) >= line_no + 1
		assert self.err[line_no] == term

	def assert_out_line_is( self, term: str, line_no: int ):
		assert len( self.out ) >= line_no + 1
		assert self.out[line_no] == term

	def assert_term_in_err_line( self, term: str, line_no: int ):
		assert self.err and len( self.err ) > line_no + 1
		assert term in self.err[line_no]

	def assert_term_in_stdout( self, term ):
		assert len( self.out ) > 0
		assert any( term in l for l in self.out )


cmd_list = 'list'
cmd_version = 'version'

# no command

@mark.context( library='default', config='default', takeout='default', cleanup=True )
def test_nocommand( ctx ):
	invoke( ctx, '' ).assert_term_in_err_line( 'Usage', 0 )

# list

@mark.context( library='default', config='default', takeout='default', cleanup=True )
def test_list( ctx ):
	invoke( ctx, cmd_list ).assert_term_in_stdout( 'Berlin' )

# version

@mark.context( library='default', config='default', takeout='default', cleanup=True )
def test_version( ctx ):
	invoke( ctx, cmd_version ).assert_out_line_is( '0.1.0', 0 )

def invoke( ctx: ApplicationContext, cmdline: str ) -> Invocation:
	runner = CliRunner( mix_stderr=False )
	cmdline = f'-c {ctx.config_dir} {cmdline}'
	result = runner.invoke( cli, cmdline )
	return Invocation( result.exit_code, result.stdout.splitlines(), result.stderr.splitlines() )

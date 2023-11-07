
from logging import getLogger
from typing import List

from attrs import define, field
from click.testing import CliRunner, Result
from pytest import mark

from tracs.cli import cli
from tracs.config import ApplicationContext

log = getLogger( __name__ )

@define
class Invocation:

	result: Result = field( default=None )
	code: int = field( default=None )
	out: List[str] = field( factory=list )
	err: List[str] = field( factory=list )

	def __attrs_post_init__( self ):
		self.code = self.result.exit_code
		self.out = self.result.stdout.splitlines()
		self.err = self.result.stderr.splitlines()

	# certain line equals term

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
		assert len( self.out ) > 0 and any( term in l for l in self.out )

cmd_list = 'list'
cmd_version = 'version'

# no command

@mark.context( env='default', persist='clone', cleanup=True )
def test_nocommand( ctx ):
	invoke( ctx, '' ).assert_term_in_err_line( 'Usage', 0 )

# list

@mark.context( env='default', persist='clone', cleanup=True )
def test_list( ctx ):
	invoke( ctx, cmd_list ).assert_term_in_stdout( 'Run at Noon' )

# version

@mark.context( env='default', persist='clone', cleanup=True )
def test_version( ctx ):
	invoke( ctx, cmd_version ).assert_out_line_is( '0.1.0', 0 )

def invoke( ctx: ApplicationContext, cmdline: str ) -> Invocation:
	runner = CliRunner( mix_stderr=False )
	cmdline = f'-c {ctx.config_dir} {cmdline}'

	log.info( f'invoking command line: {cmdline}' )
	result = runner.invoke( cli, cmdline, catch_exceptions=False )

	ctx.console.print( result.exc_info )
	return Invocation( result )

from enum import Enum
from logging import getLogger
from typing import Any, List, Optional

from attrs import define, field
from click.testing import CliRunner, Result
from pytest import mark

from tracs.cli import cli
from tracs.config import ApplicationContext

log = getLogger( __name__ )

@define( eq=False, repr=False )
class Lines:

	__data__: List[str] = field( default=None, alias='__data__' )

	def __eq__( self, other ):
		if isinstance( other, str ):
			other = [] if other == '' else [other]
		return self.__data__ == other

	def __contains__( self, item ):
		return self.__data__.__contains__( item )

	def __iter__( self ):
		return self.__data__.__iter__()

	def __repr__( self ) -> str:
		return repr( self.__data__ )

	def __str__( self ) -> str:
		return str( self.__data__ )

	def contains( self, term: str ):
		return any( term in l for l in self.__data__ )

	def contains_all( self, *terms: str ):
		return all( [ self.contains( t ) for t in terms ] )

@define
class Invocation:

	result: Result = field( default=None )

	@property
	def code( self ) -> int:
		return self.result.exit_code

	@property
	def out( self ) -> Lines:
		return Lines( self.result.stdout.splitlines() )

	@property
	def err( self ) -> Lines:
		return Lines( self.result.stderr.splitlines() )

cmd_list = 'list'
cmd_version = 'version'

# no command

@mark.context( env='default', persist='clone', cleanup=True )
def test_nocommand( ctx ):
	i = invoke( ctx, '' )
	assert i.out == ''
	assert i.err.contains_all( 'Usage', 'Error: Missing command' )

# list

@mark.context( env='default', persist='clone', cleanup=True )
def test_list( ctx ):
	i = invoke( ctx, cmd_list )
	assert i.out.contains( 'Run at Noon' )

# version

@mark.context( env='default', persist='clone', cleanup=True )
def test_version( ctx ):
	assert invoke( ctx, cmd_version ).out == '0.1.0'

def invoke( ctx: ApplicationContext, cmdline: str ) -> Invocation:
	runner = CliRunner( mix_stderr=False )
	cmdline = f'-c {ctx.config_dir} {cmdline}'

	log.info( f'invoking command line: {cmdline}' )
	result = runner.invoke( cli, cmdline, catch_exceptions=False )

	ctx.console.print( result.exc_info )
	return Invocation( result )

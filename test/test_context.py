from fs.appfs import UserConfigFS, UserDataFS
from fs.base import FS
from fs.errors import NoSysPath
from fs.memoryfs import MemoryFS
from fs.subfs import SubFS
from pytest import mark, raises

from tracs.constants import CONFIG_FILENAME, STATE_FILENAME
from tracs.context import ApplicationContext

@mark.context( env='empty', persist='clone', cleanup=True )
def test_context( fs: FS ):
	std_cfg_fs = UserConfigFS( 'tracs', create=True )
	std_lib_fs = UserDataFS( 'tracs', create=True )

	# create default context, points to user config/data fs
	ctx = ApplicationContext()

	assert ctx.config_fs.getsyspath( '' ) == std_cfg_fs.getsyspath( '' )
	ctx.config_fs = None
	assert ctx.config_fs.getsyspath( '' ) == std_cfg_fs.getsyspath( '' )
	assert ctx.config_dir == std_cfg_fs.getsyspath( '' )
	assert ctx.config_file == std_cfg_fs.getsyspath( CONFIG_FILENAME )
	assert ctx.state_file == std_cfg_fs.getsyspath( STATE_FILENAME )

	assert ctx.lib_fs.getsyspath( '' ) == std_lib_fs.getsyspath( '' )
	assert ctx.lib_dir == std_lib_fs.getsyspath( '' )
	assert ctx.db_dir == std_lib_fs.getsyspath( 'db' )

	# this should not fail
	ctx._load_configuration()

	# adjust fs after creation, use temp fs created as fixture
	ctx.config_fs = fs
	ctx.lib_fs = fs
	assert ctx.config_dir == fs.getsyspath( '' )
	assert ctx.lib_dir == fs.getsyspath( '' )

	assert ctx.db_dir == fs.getsyspath( 'db' )
	assert ctx.overlay_dir == fs.getsyspath( 'overlay' )
	assert ctx.takeouts_dir == fs.getsyspath( 'takeouts' )
	assert ctx.takeout_dir( 'polar' ) == fs.getsyspath( 'takeouts/polar/' )

	# use strings instead of fs of configuring config and lib fs
	ctx.config_fs = fs.getsyspath( '' )
	ctx.lib_fs = fs.getsyspath( '' )
	assert ctx.config_dir == fs.getsyspath( '' )
	assert ctx.lib_dir == fs.getsyspath( '' )

	ctx.config_fs = fs.getsyspath( 'config.yaml' )
	assert ctx.config_dir == fs.getsyspath( '' )

	# try memory fs
	ctx.config_fs = MemoryFS()
	assert type( ctx.config_fs ) is MemoryFS
	with raises( NoSysPath ):
		assert ctx.config_dir
	assert type( ctx.var_fs ) in [MemoryFS, SubFS]

	# create context using kwargs
	config_file_path = fs.getsyspath( 'config.yaml' )
	ctx = ApplicationContext( _cli_kwargs= { 'configuration': config_file_path } )
	assert ctx.config_dir == fs.getsyspath( '' )
	assert ctx.config_file == config_file_path

@mark.context
def test_default_context( ctx: ApplicationContext ):
	# this should result in a ctx with a memory backend -> just for easy testing
	assert type( ctx.config_fs ) is MemoryFS
	assert type( ctx.lib_fs ) in [MemoryFS, SubFS]

	assert ctx.config_fs.listdir( '/' ) != []
	assert ctx.lib_fs.listdir( '/db' ) == []

@mark.context( env='default', persist='mem' )
def test_mem_context( ctx: ApplicationContext ):
	# this should result in a ctx with memory as backend, with the default environment loaded
	assert type( ctx.config_fs ) is MemoryFS
	assert type( ctx.lib_fs ) in [MemoryFS, SubFS]

	assert ctx.config_fs.listdir( '/' )
	assert ctx.lib_fs.listdir( '/db' ) != []

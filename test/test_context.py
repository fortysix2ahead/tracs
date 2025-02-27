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

	ctx._load_configuration()

	# adjust fs after creation

	ctx.config_fs = fs
	ctx.lib_fs = fs
	assert ctx.config_dir == fs.getsyspath( '' )
	assert ctx.lib_dir == fs.getsyspath( '' )

	assert ctx.db_dir == fs.getsyspath( 'db' )
	assert ctx.overlay_dir == fs.getsyspath( 'overlay' )
	assert ctx.takeouts_dir == fs.getsyspath( 'takeouts' )
	assert ctx.takeout_dir( 'polar' ) == fs.getsyspath( 'takeouts/polar/' )

	# use strings instead of fs of configuraing config and lib fs

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

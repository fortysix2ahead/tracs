from fs.appfs import UserConfigFS, UserDataFS
from fs.base import FS
from pytest import mark

from tracs.constants import CONFIG_FILENAME, STATE_FILENAME
from tracs.context import ApplicationContext

@mark.context( env='empty', persist='clone', cleanup=True )
def test_default_context( fs: FS ):
	std_cfg_fs = UserConfigFS( 'tracs', create=True )
	std_lib_fs = UserDataFS( 'tracs', create=True )

	# create default context, points to user config/data fs
	ctx = ApplicationContext()

	assert ctx.config_fs.getsyspath( '' ) == std_cfg_fs.getsyspath( '' )
	assert ctx.config_dir == std_cfg_fs.getsyspath( '' )
	assert ctx.config_file == std_cfg_fs.getsyspath( CONFIG_FILENAME )
	assert ctx.state_file == std_cfg_fs.getsyspath( STATE_FILENAME )

	assert ctx.lib_fs.getsyspath( '' ) == std_lib_fs.getsyspath( '' )
	assert ctx.lib_dir == std_lib_fs.getsyspath( '' )

	assert ctx.db_fs is None # db does not yet exist

	ctx.apply_config() # this creates all internal FS objects

	assert ctx.db_dir == std_lib_fs.getsyspath( 'db' )

@mark.context( env='empty', persist='clone', cleanup=True )
def test_custom_context( fs: FS ):
	ctx = ApplicationContext( _init_with={ 'configuration': fs.getsyspath( '' ) } )

	assert ctx.config_fs.getsyspath( '' ) == fs.getsyspath( '' )
	assert ctx.config_dir == fs.getsyspath( '' )
	assert ctx.config_file == fs.getsyspath( CONFIG_FILENAME )
	assert ctx.state_file == fs.getsyspath( STATE_FILENAME )

	assert ctx.lib_fs.getsyspath( '' ) == fs.getsyspath( '' )
	assert ctx.lib_dir == fs.getsyspath( '' )
	assert ctx.db_dir == fs.getsyspath( 'db' )

	assert ctx.overlay_dir == fs.getsyspath( 'overlay' )
	assert ctx.takeouts_dir == fs.getsyspath( 'takeouts' )
	assert ctx.takeout_dir( 'polar' ) == fs.getsyspath( 'takeouts/polar/' )


from confuse import Configuration

class Plugin:

	def __init__( self, cfg: Configuration = None, global_cfg: Configuration = None ) -> None:
		self._cfg = cfg
		self._global_cfg = global_cfg

	@property
	def cfg( self ) -> Configuration:
		return self._cfg

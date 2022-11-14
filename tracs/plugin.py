from logging import getLogger
from typing import Any

from confuse import Configuration
from confuse import NotFoundError

from tracs.config import ApplicationContext
from tracs.config import KEY_PLUGINS

log = getLogger( __name__ )

class Plugin:

	def __init__( self, **kwargs ) -> None:
		self._ctx: ApplicationContext = kwargs.get( 'ctx' ) # field for saving the current context, to access the context from sub-methods
		self._cfg: Configuration = self._ctx.config if self._ctx else None
		self._state: Configuration = self._ctx.state if self._ctx else None

	# helpers for setting/getting plugin configuration/state values

	def cfg_value( self, key: str ) -> Any:
		try:
			return self._cfg[KEY_PLUGINS][self._name][key].get()
		except NotFoundError:
			log.error( f'missing configuration key {key}', exc_info=True )

	def state_value( self, key: str ) -> Any:
		try:
			return self._state[KEY_PLUGINS][self._name][key].get()
		except NotFoundError:
			log.error( f'missing state key {key}', exc_info=True )

	def set_cfg_value( self, key: str, value: Any ) -> None:
		self._cfg[KEY_PLUGINS][self._name][key] = value

	def set_state_value( self, key: str, value: Any ) -> None:
		self._state[KEY_PLUGINS][self._name][key] = value


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
		self._name: str = kwargs.pop( 'name' ) if 'name' in kwargs else self.__class__.__name__.lower()
		self._display_name = kwargs.pop( 'display_name' ) if 'display_name' in kwargs else self.__class__.__name__
		self._cfg: Configuration = self._ctx.config if self._ctx else None
		self._state: Configuration = self._ctx.state if self._ctx else None

		self._enabled = True

	# helpers for setting/getting plugin configuration/state values

	def cfg_value( self, key: str ) -> Any:
		try:
			return self._cfg[KEY_PLUGINS][self.name][key].get()
		except NotFoundError:
			log.error( f'missing configuration key {key}', exc_info=True )

	def state_value( self, key: str ) -> Any:
		try:
			return self._state[KEY_PLUGINS][self.name][key].get()
		except NotFoundError:
			log.error( f'missing state key {key}', exc_info=True )

	def set_cfg_value( self, key: str, value: Any ) -> None:
		self._cfg[KEY_PLUGINS][self.name][key] = value

	def set_state_value( self, key: str, value: Any ) -> None:
		self._state[KEY_PLUGINS][self.name][key] = value

	@property
	def ctx( self ) -> ApplicationContext:
		"""
		Returns the application context this plugin lives in.

		:return: application context object
		"""
		return self._ctx

	@property
	def name( self ) -> str:
		"""
		Returns the name of this plugin. Default to the lower case name of the plugin class.

		:return: name of the plugin
		"""
		return self._name

	@property
	def display_name( self ) -> str:
		"""
		Returns the display name of this plugin. Default to the name of the plugin class.

		:return: display name of the plugin
		"""
		return self._display_name

	@property
	def enabled( self ) -> bool:
		"""
		Returns if this plugin is enabled.

		:return: enabled state
		"""
		return True

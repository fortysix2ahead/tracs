from logging import getLogger
from typing import Any, Tuple

from dynaconf import Dynaconf as Configuration
from dynaconf.utils.boxing import DynaBox

from tracs.config import ApplicationContext
from tracs.db import ActivityDb

log = getLogger( __name__ )

class Plugin:

	def __init__( self, *args, **kwargs ) -> None:
		# configure name and display_name: this is optional
		self._name: str = kwargs.get( 'name', self.__class__.__name__.lower() )
		self._display_name: str = kwargs.get( 'display_name', self.__class__.__name__ )

		# save the current context, to be able to access the context from sub-methods
		self._ctx: ApplicationContext = kwargs.get( 'ctx' )
		if self._ctx:
			# configure config/state views: create empty configs if context is missing
			try:
				self._cfg: DynaBox = self._ctx.config.plugins[self.name]
			except AttributeError:
				self._cfg = DynaBox()

			try:
				self._state: DynaBox = self._ctx.state.plugins[self.name]
			except AttributeError:
				self._state = DynaBox()

		elif kwargs.get( '_configuration' ) and kwargs.get( '_state' ): # this is mainly for testing purposes
			self._cfg = kwargs.get( '_configuration' )
			self._state = kwargs.get( '_state' )

		else: # fallback
			self._cfg, self._state = DynaBox(), DynaBox()

		# enable by default
		self._cfg.enabled = kwargs.get( 'enabled', True )

	# helpers for setting/getting plugin configuration/state values

	@property
	def cs( self ) -> Tuple[Configuration, Configuration]:
		"""
		Returns a tuple with plugin configuration and state.
		:return: tuple with configuration and state
		"""
		return self._cfg, self._state

	def cfg_value( self, key: str ) -> Any:
		return self.config_value( key )

	def config_value( self, key: str, default: Any = None ) -> Any:
		try:
			return self._cfg[key].get()
		except NotFoundError:
			log.error( f'missing configuration key {key}', exc_info=True )
			return default

	def state_value( self, key: str, default: Any = None ) -> Any:
		try:
			return self._state[key].get()
		except NotFoundError:
			log.error( f'missing state key {key}', exc_info=True )
			return default

	def set_cfg_value( self, key: str, value: Any ) -> None:
		self.set_config_value( key, value )

	def set_config_value( self, key: str, value: Any ) -> None:
		self._cfg[key] = value

	def set_state_value( self, key: str, value: Any ) -> None:
		self._state[key] = value

	@property
	def ctx( self ) -> ApplicationContext:
		"""
		Returns the application context this plugin lives in.

		:return: application context object
		"""
		return self._ctx

	@property
	def db( self ) -> ActivityDb:
		"""
		Returns the db associated with the context.

		:return: db
		"""
		return self._ctx.db if self._ctx else None

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
		return self.config_value( 'enabled' )

from typing import Optional

class ImportException( Exception ):
	"""Exception raised in case imports are failing.
	"""

	def __init__( self, message: str, cause: Optional[Exception] = None ):
		super().__init__()
		self.__message__ = message
		self.__cause__ = cause

class ResourceImportException( Exception ):

	def __init__( self, message: str, cause: Optional[Exception] = None ):
		super().__init__()
		self.__message__ = message
		self.__cause__ = cause


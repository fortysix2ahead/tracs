from typing import Optional

class ResourceImportException( Exception ):

	def __init__( self, message: str, cause: Optional[Exception] ):
		super().__init__()
		self.__message__ = message
		self.__cause__ = cause

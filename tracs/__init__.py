from __future__ import annotations

from logging import getLogger

from tracs.__log__ import LogManager

# create root logger 'tracs' + log manager
log = getLogger( __name__ )
log_mgr = LogManager.instance( root=log, debug=False, verbose=False )

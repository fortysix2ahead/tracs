
from logging import getLogger
from pathlib import Path

from gpxpy import parse as parse_gpx
from gpxpy.gpx import GPX
from gpxpy.gpx import GPXTrackPoint
from gpxpy.gpx import GPXXMLSyntaxException
from lxml import etree
from lxml.sax import ContentHandler
from lxml.sax import saxify

from .config import ApplicationConfig as cfg

log = getLogger( __name__ )

def read_gpx( path: Path ) -> GPX:
	parser_mode = cfg['gpx'].get()['parser']
	if parser_mode == 'internal':
		return _fast_parse( path )
	else:
		return _default_parse( path )

def _default_parse( path: Path ) -> GPX:
	try:
		return parse_gpx( open( path, encoding='utf-8', mode='r' ) )
	except GPXXMLSyntaxException:
		log.error( f"unable to read GPX from {path}" )

def _fast_parse( path: Path ) -> GPX:
	with open( path, encoding='utf8' ) as file:
		root = etree.fromstring( bytes( file.read(), encoding='utf-8' ) )
		handler = GpxContentHandler()
		saxify( root, handler )
		return handler.gpx

class GpxContentHandler( ContentHandler ):

	def __init__( self ):
		super().__init__()
		self.gpx = None

		self.stack = []
		self.points = []
		self.ele = None
		self.lat = None
		self.lon = None
		self.point = None
		self.text = None
		self.time = None

	def startElementNS(self, name, qname, attributes):
		uri, localname = name
		self.stack.append( localname )

		if localname == 'trkpt':
			self.lat = float( attributes.get( (None, 'lat'), 0.0 ) )
			self.lon = float( attributes.get( (None, 'lon'), 0.0 ) )
			self.ele = None
			self.time = None
		elif localname == 'gpx':
			self.gpx = GPX()

	def endElementNS( self, name, qname ):
		uri, localname = name
		if localname == 'ele':
			ele = float( self.text )
		elif localname == 'time':
			self.time = self.text
		elif localname == 'trkpt':
			self.points.append( GPXTrackPoint( float( self.lat ), float( self.lon ), self.ele, self.time ) )

		self.stack.pop()

	def characters( self, content ):
		self.text = content

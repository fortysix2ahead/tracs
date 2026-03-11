from pathlib import Path
from typing import Any, Optional

#from tracs.models.polar.constants import POLAR_EXERCISE_DATA_TYPE
from tracs.pluginmgr import importer
from tracs.plugins.xml import XMLHandler

# @importer( type=POLAR_EXERCISE_DATA_TYPE )
class PersonalTrainerImporter( XMLHandler ):

	def __init__( self ) -> None:
		super().__init__()

	def load_data( self, data: Any, text: Optional[str], content: Optional[bytes], path: Optional[Path], url: Optional[str] ) -> Any:
		xml = super().load_data( data, text, content, path, url )
		root = xml.getroot()
		data = {
			'time': root.find( self._ns( 'calendar-items/exercise/time' ) ).text,
			'type': root.find( self._ns( 'calendar-items/exercise/sport' ) ).text,
			'result_type': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/sport' ) ).text,  # should be the same as type
			'duration': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/duration' ) ).text,  # should be the same as type
			'distance': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/distance' ) ).text,
			'calories': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/calories' ) ).text,
			'recording_rate': root.find( self._ns( 'calendar-items/exercise/sport-results/sport-result/recording-rate' ) ).text,
		}
		samples = root.findall( self._ns( 'calendar-items/exercise/sport-results/sport-result/samples/sample' ) )
		for s in samples:
			sample_type = s.find( self._ns( 'type' ) ).text
			sample_values = s.find( self._ns( 'values' ) ).text
			data[('samples', sample_type)] = sample_values.split( ',' )
		return data

	# noinspection PyMethodMayBeStatic
	def _ns( self, s: str ):
		return f'{{{PED_NS}}}' + s.replace( '/', f'/{{{PED_NS}}}' )


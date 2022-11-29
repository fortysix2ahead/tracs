
from tracs.resources import Resource
from tracs.service import Service

def test_filter_fetched():
	resources = [
		Resource( uid='polar:10' ),
		Resource( uid='polar:20' ),
		Resource( uid='polar:30' ),
	]

	service = Service()
	assert service.filter_fetched( resources, 'polar:20' ) == [resources[1]]
	assert service.filter_fetched( resources, 'polar:10', 'polar:20' ) == [resources[0], resources[1]]
	assert service.filter_fetched( resources, *[r.uid for r in resources] ) == resources
	assert service.filter_fetched( resources ) == resources

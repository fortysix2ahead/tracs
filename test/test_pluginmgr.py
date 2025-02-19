from pluginmgr import PluginManager

def test_pluginmgr():
	PluginManager.init()

	assert len( PluginManager.plugins ) > 0
	assert len( PluginManager.decorators ) > 0

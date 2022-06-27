from evaluation_system.test.mocks import DummyPlugin

plugin = DummyPlugin()
plugin.add_output_to_databrowser(".docker/data", variable="precipitation")

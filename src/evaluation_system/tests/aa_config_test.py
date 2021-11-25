
import os
import pytest
import mock
from pathlib import Path
from tempfile import NamedTemporaryFile

def mockenv(**envvars):
    return mock.patch.dict(os.environ, envvars)


class MockConfigFile:

    def __init__(self, env_vars):

        self._tf = NamedTemporaryFile(suffix='.conf')
        self.name = self._tf.name
        env_vars['EVALUATION_SYSTEM_CONFIG_FILE'] = self.name
        self.mock_env = mockenv(**env_vars)
        self.mock_env.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._tf.close()
        self.mock_env.stop()

def mock_config_file(env_vars):

    with NamedTemporaryFile(suffix='.conf') as tf:
        env_vars['EVALUATION_SYSTEM_CONFIG_FILE'] = tf.name
        with mockenv(**env_vars):
            return tf

@mockenv(PUBKEY='')
def test_wrong_config():
    from evaluation_system.misc import config
    with pytest.raises(FileNotFoundError):
         config._get_public_key('no_such_project')

def test_vault(dummy_key, requests_mock, dummy_env):
    from configparser import ConfigParser, ExtendedInterpolation
    from evaluation_system.misc import config
    mockenv(PUBKEY=dummy_key)
    db_cfg = {}
    for key in ('host', 'user', 'passwd', 'db'):
        db_cfg[f'db.{key}'] = dummy_env['evaluation_system'][f'db.{key}']
    sha = config._get_public_key('test_system')
    url = f'http://{db_cfg["db.host"]}:5003/vault/data/{sha}'
    requests_mock.get(url, json=db_cfg)
    for key in ('db.passwd', 'db.user', 'db.db'):
        assert config._read_secrets(sha, key, db_cfg['db.host'], port=5003,
                protocol='http') == db_cfg[key]

def test_get(dummy_env):
    from evaluation_system.misc import config
    config.reloadConfiguration()
    base_dir = config.get(config.BASE_DIR)
    assert base_dir == 'evaluation_system'
    with pytest.raises(config.ConfigurationException):
        config.get('non-existing-key')
    assert config.get('non-existing-key', 'default-answer') == 'default-answer'

def test_keys(dummy_env):
    from evaluation_system.misc import config
    keys = config.keys()
    assert len(keys) >= 2
    assert config.BASE_DIR in keys

def test_reload(dummy_env):
    """Test we can reload the configuration"""
    from evaluation_system.misc import config
    try:
        config._config[config.BASE_DIR_LOCATION] = 'TEST'
        c1 = config.get(config.BASE_DIR_LOCATION)
        assert c1 == 'TEST'
    finally:
        config.reloadConfiguration()
    c2 = config.get(config.BASE_DIR_LOCATION)
    assert c1 != c2

def test_DIRECTORY_STRUCTURE():
    from evaluation_system.misc import config
    assert config.DIRECTORY_STRUCTURE.validate('local')
    assert config.DIRECTORY_STRUCTURE.validate('central')
    assert not config.DIRECTORY_STRUCTURE.validate('asdasdasdasdss')

def test_config_file(dummy_key):
    """If a config file is provided it should be read"""
    from evaluation_system.misc import config
    assert config.get(config.BASE_DIR) == 'evaluation_system'
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write('[evaluation_system]\n%s=nowhere\nproject_name=test_system\ndb.host=localhost' % config.BASE_DIR)
        config.reloadConfiguration()
        assert config.get(config.BASE_DIR) == 'nowhere'
        # check wrong section
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write('[wrong_section]\n%s=nowhere\n' % config.BASE_DIR)
        with pytest.raises(config.ConfigurationException):
            config.reloadConfiguration()
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write(
                    f'''[evaluation_system]
{config.DIRECTORY_STRUCTURE_TYPE}=wrong_value
project_name=test_system
db.host=localhost'''
            )
        with pytest.raises(config.ConfigurationException):
            config.reloadConfiguration()
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write(
                    f'''[evaluation_system]
{config.BASE_DIR}=$$EVALUATION_SYSTEM_HOME
project_name=test_system
db.host=localhost'''
            )
        assert config.get(config.BASE_DIR) == 'evaluation_system'
        config.reloadConfiguration()
        assert config.get(config.BASE_DIR) == \
                          '/'.join(__file__.split('/')[:-4])

def test_plugin_conf(dummy_key):
    from evaluation_system.misc import config
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write("""
[evaluation_system]
base_dir=~
project_name=test_system
db.host=localhost

[plugin:pca]
plugin_path=$$EVALUATION_SYSTEM_HOME/tool/pca
python_path=$$EVALUATION_SYSTEM_HOME/tool/pca/integration
module=pca.api

[plugin:climval]
plugin_path=$$EVALUATION_SYSTEM_HOME/tool/climval
python_path=$$EVALUATION_SYSTEM_HOME/tool/climval/src
module=climval.tool
"""
)

        config.reloadConfiguration()
        plugins_dict = config.get(config.PLUGINS)
        assert set(plugins_dict) == set(['pca', 'climval'])
        es_home = '/'.join(__file__.split('/')[:-4])
        assert config.get_plugin('pca', config.PLUGIN_PATH) == \
                          es_home + '/tool/pca'
        assert config.get_plugin('pca', config.PLUGIN_PYTHON_PATH) == \
                          es_home + '/tool/pca/integration'
        assert config.get_plugin('pca', config.PLUGIN_MODULE) == \
                          'pca.api'
        assert config.get_plugin('pca', 'not_existing', 'some_default') == \
                          'some_default'

        assert config.get_plugin('climval', config.PLUGIN_MODULE) == \
                          'climval.tool'
        with pytest.raises(config.ConfigurationException):
            config.get_plugin('climval', 'missing_modules')

def test_get_section(dummy_key):
    from evaluation_system.misc import config
    with MockConfigFile({'PUBKEY': dummy_key}) as tf:
        with open(tf.name, 'w') as f:
            f.write("""[evaluation_system]
base_dir=/home/lala
project_name=test_proj
db.host=localhost

[some_other_section]
param=value
some=val

"""
)
        config.reloadConfiguration()
        eval_sect = config.get_section('evaluation_system')
        assert eval_sect == {
                'base_dir': '/home/lala', 'project_name': 'test_proj',
                'db.host': 'localhost'
        }
        other = config.get_section('some_other_section')
        assert other == {'param': 'value', 'some': 'val'}
        with pytest.raises(config.NoSectionError):
            config.get_section('novalid_section')

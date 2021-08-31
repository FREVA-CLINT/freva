
import os
import pytest
import mock
from pathlib import Path

def mockenv(**envvars):
    return mock.patch.dict(os.environ, envvars)



@mockenv(PUBKEY='')
def test_wrong_config():
    from evaluation_system.misc import config
    #env = os.environ.copy()
    #os.environ.pop('PUBKEY', None)
    with pytest.raises(FileNotFoundError):
         config._get_public_key('false.crt')
    #os.environ = env.copy()
    config.reloadConfiguration()
    
def test_vault(dummy_key, requests_mock):
    from configparser import ConfigParser, ExtendedInterpolation
    from evaluation_system.misc import config
    os.environ['PUBKEY'] = dummy_key
    cfg = ConfigParser(interpolation=ExtendedInterpolation())
    with (Path(__file__).parent / 'test.conf').open() as f:
        cfg.read_file(f)
        db_cfg = {}
        for key in ('host', 'user', 'passwd', 'db'):
            db_cfg[f'db.{key}'] = cfg['evaluation_system'][f'db.{key}']
    sha = config._get_public_key('false.crt')
    url = f'http://{db_cfg["db.host"]}:5003/vault/data/{sha}'
    requests_mock.get(url, json=db_cfg)
    for key in ('db.passwd', 'db.user', 'db.db'):
        assert config._read_secrets(sha, key, db_cfg['db.host'], port=5003,
                protocol='http') == db_cfg[key]

def test_get():
    from evaluation_system.misc import config
    config.reloadConfiguration()
    base_dir = config.get(config.BASE_DIR)
    assert base_dir == 'evaluation_system'
    with pytest.raises(config.ConfigurationException):
        config.get('non-existing-key')
    assert config.get('non-existing-key', 'default-answer') == 'default-answer'

def test_keys():
    from evaluation_system.misc import config
    keys = config.keys()
    assert len(keys) >= 2
    assert config.BASE_DIR in keys

def test_reload():
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
    import tempfile
    os.environ['PUBKEY'] = dummy_key
    fd, name = tempfile.mkstemp(__name__, text=True)
    with os.fdopen(fd, 'w') as f:
        f.write('[evaluation_system]\n%s=nowhere\nproject_name=test_system\ndb.host=localhost' % config.BASE_DIR)
    assert config.get(config.BASE_DIR) == 'evaluation_system'
    try:
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        assert config.get(config.BASE_DIR) == 'nowhere'
        os.unlink(name)
        # check wrong section
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[wrong_section]\n%s=nowhere\n' % config.BASE_DIR)

        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        with pytest.raises(config.ConfigurationException):
            config.reloadConfiguration()

        os.unlink(name)

        # check directory structure value
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[evaluation_system]\n%s=wrong_value\nproject_name=test_system\ndb.host=localhost' % config.DIRECTORY_STRUCTURE_TYPE)

        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        with pytest.raises(config.ConfigurationException):
            config.reloadConfiguration()

        os.unlink(name)

        # check $EVALUATION_SYSTEM_HOME get's resolved properly
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[evaluation_system]\n%s=$$EVALUATION_SYSTEM_HOME\nproject_name=test_system\ndb.host=localhost' % config.BASE_DIR)

        assert config.get(config.BASE_DIR) == 'evaluation_system'
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        assert config.get(config.BASE_DIR) == \
                          '/'.join(__file__.split('/')[:-4])

    finally:
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        os.environ['PUBKEY'] = dummy_key
        os.unlink(name)

def test_plugin_conf(dummy_key):
    import tempfile
    from evaluation_system.misc import config
    os.environ['PUBKEY'] = dummy_key
    fd, name = tempfile.mkstemp(__name__, text=True)
    with os.fdopen(fd, 'w') as f:
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

""")

    os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
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
    os.unlink(name)

def test_get_section(dummy_key):
    import tempfile
    from evaluation_system.misc import config
    os.environ['PUBKEY'] = dummy_key
    fd, name = tempfile.mkstemp(__name__, text=True)
    with os.fdopen(fd, 'w') as f:
        f.write("""
[evaluation_system]
base_dir=/home/lala
project_name=test_proj
db.host=localhost

[some_other_section]
param=value
some=val

""")
    os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
    config.reloadConfiguration()
    eval = config.get_section('evaluation_system')
    assert eval == {'base_dir': '/home/lala', 'project_name': 'test_proj',
                    'db.host': 'localhost'}
    other = config.get_section('some_other_section')
    assert other == {'param': 'value', 'some': 'val'}

    # no valid section
    # config.get_section('safasfas')
    with pytest.raises(config.NoSectionError):
        config.get_section('novalid_section')

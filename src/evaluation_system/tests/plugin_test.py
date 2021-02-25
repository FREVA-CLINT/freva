"""
Created on 13.05.2016

@author: Sebastian Illing
"""

import os
import datetime
from pathlib import Path
import pytest
from tempfile import NamedTemporaryFile
import sys

from evaluation_system.tests import similar_string


def test_incomplete_abstract(dummy_plugin):
    # this is an incomplete class not implementing all required fields
    from evaluation_system.api.plugin import PluginAbstract
    class Incomplete(PluginAbstract):
        pass
    with pytest.raises(TypeError):
        Incomplete()

def test_complete_abstract(dummy_plugin):
    """Tests the creation of a complete implementation of the Plugin Abstract class"""
    # even though py it's just a stub, it should be complete.
    from evaluation_system.tests.mocks.dummy import DummyPlugin
    assert type(dummy_plugin) == type(DummyPlugin())

def test_setup_configuration(dummy_plugin):
    from evaluation_system.tests.mocks.dummy import DummyUser, DummyPlugin
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  ValidationError,
                                                  String)
    with DummyUser(random_home=True) as user:
        dummy = DummyPlugin(user=user)
        dummy.__parameters__ = ParameterDictionary(String(name='a',
                                                          mandatory=True))
        # the default behavior is to check for None values and fail if found
        with pytest.raises(ValidationError):
            dummy.setupConfiguration()

        # it can be turned off
        res = dummy.setupConfiguration(check_cfg=False)
        assert res == {'a': None}

        # check template
        res = dummy.setupConfiguration(dict(num=1), check_cfg=False)
        assert 1 == res['num']

        # check indirect resolution
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),
                                       check_cfg=False)
        assert "1x" == res['num']

        # check indirect resolution can also be turned off
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),
                                       check_cfg=False, recursion=False)
        assert "${a}x" == res['num']

        # check user special values work
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),
                                       check_cfg=False)
        assert user.getUserBaseDir() == res['num']

        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),
                                       check_cfg=False, substitute=False)
        assert '$USER_BASE_DIR' == res['num']


def test_parse_arguments(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary, String,
                                                  Integer, ValidationError,
                                                  Bool)
    dummy = dummy_plugin
    dummy.__parameters__ = ParameterDictionary(String(name='a'),
                                               String(name='b'))
    res = dummy.__parameters__.parseArguments("a=1 b=2".split())
    assert res == dict(a='1', b='2')
    dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', default=0),
            Integer(name='b', default=0)
    )
    res = dummy.__parameters__.parseArguments("a=1 b=2".split())
    assert res == dict(a=1, b=2)
    # even if the default value is different, the metadata can define the type
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', default='1'), Integer(name='b', default=2)
    )
    res = dummy.__parameters__.parseArguments("a=1 b=2".split())
    assert res == dict(a=1, b=2)
    # more arguments than those expected
    dummy.__parameters__ = ParameterDictionary(Integer(name='a',
                                                       default='1'))
    with pytest.raises(ValidationError):
        dummy.__parameters__.parseArguments("a=1 b=2".split())
    dummy.__parameters__ = ParameterDictionary(Bool(name='a'))
    for arg, parsed_val in [("a=1", True), ("a=true", True), ("a=TRUE", True),
                            ("a=0", False), ("a=false", False),
                            ("a=False", False)]:
        res = dummy.__parameters__.parseArguments(arg.split())
        assert res == dict(a=parsed_val), \
                         'Error when parsing %s, got %s' % (arg, res)

def test_parse_metadict(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary, String,
                                                  Integer, Bool, Float,
                                                  ValidationError)
    dummy = dummy_plugin
    for d, res_d in [(Integer(name='a', default=0), 1),
                     (Integer(name='a'), 1),
                     (Integer(name='a', default='0'), 1),
                     (String(name='a'), '1'),
                     (String(name='a', default=1), '1'),
                     (Bool(name='a'), True),
                     (Float(name='a'), float('1'))]:
        dummy.__parameters__ = ParameterDictionary(d)
        res = dummy._parseConfigStrValue('a', '1')
        assert res == res_d

    # check errors
    # Wrong type
    dummy.__parameters__ = ParameterDictionary(Integer(name='a'))
    with pytest.raises(ValidationError):
        dummy._parseConfigStrValue('a', 'd')
    # wrong key
    with pytest.raises(ValidationError):
        dummy._parseConfigStrValue('b', '1')

def test_read_config_parser(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary, String,
                                                  Integer, ValidationError)
    from configparser import ConfigParser
    from io import StringIO
    conf = ConfigParser()
    conf_str = "[DummyPlugin]\na=42\nb=text"
    conf.readfp(StringIO(conf_str))
    dummy = dummy_plugin
    # check parsing
    for d, res_d in [([Integer(name='a')], dict(a=42)),
                     ([String(name='a')], dict(a='42')),
                     ([Integer(name='a'), String(name='b')],
                      dict(a=42, b='text'))]:
        dummy.__parameters__ = ParameterDictionary(*d)
        res = dummy.readFromConfigParser(conf)
        assert res == res_d
    # check errors
    # wrong type
    dummy.__parameters__ = ParameterDictionary(Integer(name='b'))
    with pytest.raises(ValidationError):
        dummy.readFromConfigParser(conf)
    # wrong regex
    dummy.__parameters__ = ParameterDictionary(Integer(name='a',
                                                       regex='14[0-9]*'))
    with pytest.raises(ValidationError):
        dummy.readFromConfigParser(conf)

def test_save_config(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String)
    from io import StringIO
    res_str = StringIO()
    dummy = dummy_plugin
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', help=''), Integer(name='b', help='')
    )
    tests = [(dict(a=1), '[DummyPlugin]\na=1'),
             (dict(a='1'), '[DummyPlugin]\na=1'),
             (dict(b=2), '[DummyPlugin]\nb=2')]
    for t, res in tests:
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, t)
        assert res_str.getvalue().strip('\x00').strip() == res

    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', help='This is \na test'),
        Integer(name='b', help='Also\na\ntest.')
    )
    res_str.truncate(0)
    dummy.saveConfiguration(res_str, {'a': 1})
    assert res_str.getvalue().strip('\x00').strip().strip('\x00') == \
                     '[DummyPlugin]\n#: This is\n#: a test\na=1'
    res_str.truncate(0)
    dummy.saveConfiguration(res_str, {'a': 1}, include_defaults=True)
    assert res_str.getvalue().strip('\x00').strip() == \
                     '[DummyPlugin]\n#: This is\n#: a test\na=1\n\n#: Also\n#: a\n#: test.\n#b=None'

    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', 
        help="""This is a very long and complex explanation so that we could test how it is transformed into a proper configuration file that:
a) is understandable
b) Retains somehow the format
c) its compact
We'll have to see how that works out..."""),
                                        String(name='b', mandatory=True, help='Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.'),
                                        String(name='c', help="""This is to check the format is preserved
             \..,.-
             .\   |         __
             .|    .-     /  .;
       _      _|      \__/..     \ 
      \ ...\|   X Hamburg        :_
       |                           \ 
      /                            /
     -.                           |
      \  X Rheine      Berlin X    \ 
   __/                              |
  |                                 /
  |                                 \ 
 /                                   |
 \     X Cologne        Dresden  X . ,
  \                            ._-. .
 /                        __.-/
 |         X Frankfurt    \ 
  \                        \ 
   \                        \ 
    ...,.                    \ 
        /                     \.
       /                       ,.
      /                      ./
     |         Munich X     |
     \,......,__  __,  __.-. .
                \/   -/     ..
dj1yfk"""))
    res_str.truncate(0)
    dummy.saveConfiguration(res_str, {'a': 1}, include_defaults=True)

def test_read_config(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary, Integer,
                                                  String, Float)
    dummy = dummy_plugin
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a'),
        String(name='b', default='test'),
        Float(name='other', default=1.4)
    )
    for resource, expected_dict in [(u'[DummyPlugin]\na=1',
                                     dict(a=1, b='test', other=1.4)),
                                    (u'[DummyPlugin]\na= 1 \n', dict(a=1, b='test',
                                                                      other=1.4)),
                                    (u'[DummyPlugin]\na=1\nb=2', dict(a=1, b="2",
                                                                    other=1.4)),
                                    (u'[DummyPlugin]\n#a=1\nb=2\n#asd\nother=1e10',
                                    dict(a=None, b="2", other=1e10)),
                                    (u'[DummyPlugin]\na=-2\nb=blah blah blah',
                                    dict(a=-2, b="blah blah blah", other=1.4))]:
        with NamedTemporaryFile() as tf:
            open(tf.name, 'w').write(resource)
            with open(tf.name, 'r') as f:
                conf_dict = dummy.readConfiguration(f)
                assert conf_dict == expected_dict

def testSubstitution(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    dummy = dummy_plugin
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a'), String(name='b', default='value:$a'),
        Directory(name='c', default='$USER_OUTPUT_DIR'))
    cfg_str = dummy.getCurrentConfig({'a': 72})
    assert 'value:72' in cfg_str
    assert cfg_str.startswith("""a: 72
b: - (default: value:$a [value:72])
c: - (default: $USER_OUTPUT_DIR [""")

def test_help(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String)
    dummy = dummy_plugin
    dummy.__version__ = (1, 2, 3)
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', default=1, help='This is the value of a'),
        String(name='b', help='This is not the value of b'),
        String(name='example', default='test', help="let's hope people write some useful help...")
    )

    descriptions = [('__short_description__', 'A short Description'),
                    ('__long_description__', 'A long Description')]

    for desc in descriptions:
        setattr(dummy, desc[0], desc[1])
        resource = """DummyPlugin (v1.2.3): %s
Options:
a       (default: 1)
    This is the value of a
b       (default: <undefined>)
    This is not the value of b
example (default: test)
    let's hope people write some useful help...""" % desc[1]
        assert similar_string(dummy.getHelp().strip(), resource.strip())

def test_show_config(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Float)
    from evaluation_system.tests.mocks.dummy import DummyUser, DummyPlugin
    user = DummyUser(random_home=True)
    dummy = DummyPlugin(user=user)

    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', mandatory=True, help='This is the value of a'),
        String(name='b', default='test', help='This is not the value of b'),
        Float(name='other', default=1.4, )
    )
    assert dummy.getCurrentConfig() == "    a: - *MUST BE DEFINED!*\n    b: - (default: test)\nother: - (default: 1.4)"
    assert dummy.getCurrentConfig(config_dict=dict(a=2123123)) == "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)"
    assert dummy.getCurrentConfig(config_dict=dict(a=2123123)) == "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)"
    res = dummy.getCurrentConfig(config_dict=dict(a='/tmp$USER_PLOTS_DIR'))
    cmp_str = "    a: /tmp$USER_PLOTS_DIR [/tmp" +\
                      user.getUserPlotsDir('DummyPlugin') + "]\n    b: - (default: test)\nother: - (default: 1.4)"

    assert similar_string(cmp_str, res)
    user.cleanRandomHome()

def test_usage(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String)
    dummy = dummy_plugin
    dummy.__parameters__ = ParameterDictionary(
        Integer(name='a', help='This is very important'),
        Integer(name='b', default=2),
        String(name='c', help='Well this is just an x...'))
    def_config = dummy.setupConfiguration(check_cfg=False)
    from io import StringIO
    resource = StringIO() 
    dummy.saveConfiguration(resource, def_config)
    res_str1 = resource.getvalue()
    resource.truncate(0)
    dummy.saveConfiguration(resource)
    res_str2 = resource.getvalue()
    assert res_str1.strip('\x00') == res_str2.strip('\x00')

def test_run(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    from evaluation_system.tests.mocks.dummy import DummyPlugin
    dummy = dummy_plugin
    # no config
    dummy.runTool()
    assert len(DummyPlugin._runs) == 1
    run = DummyPlugin._runs[0]
    assert run is None
    DummyPlugin._runs = []

    # direct config
    dummy.runTool(config_dict=dict(the_number=42))
    assert len(DummyPlugin._runs) == 1
    run = DummyPlugin._runs[0]
    assert 'the_number' in run
    assert run['the_number'] == 42
    DummyPlugin._runs = []

def test_get_class_base_dir(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    dummy = dummy_plugin
    import evaluation_system.tests.mocks
    import os
    import re
    assert evaluation_system.tests.\
                    mocks.dummy.__file__.startswith(dummy.getClassBaseDir())
    # module name should be getClassBaseDir() + modulename_with_"/"_instead_of_"." + ".pyc" or ".py"
    module_name = os.path.abspath(evaluation_system.tests.\
                                  mocks.dummy.__file__)[len(dummy.getClassBaseDir())+1:].replace('/', '.')
    print(module_name, 'blablabla')
    module_name = re.sub("\.pyc?$", "", module_name)
    assert module_name == 'evaluation_system.tests.mocks.dummy'

def test_special_variables():
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    from evaluation_system.tests.mocks.dummy import DummyPlugin
    dummy = DummyPlugin()
    special_vars = dict(sv_USER_BASE_DIR="$USER_BASE_DIR",
                        sv_USER_OUTPUT_DIR="$USER_OUTPUT_DIR",
                        sv_USER_PLOTS_DIR="$USER_PLOTS_DIR",
                        sv_USER_CACHE_DIR="$USER_CACHE_DIR",
                        sv_SYSTEM_DATE="$SYSTEM_DATE",
                        sv_SYSTEM_DATETIME="$SYSTEM_DATETIME",
                        sv_SYSTEM_TIMESTAMP="$SYSTEM_TIMESTAMP",
                        sv_SYSTEM_RANDOM_UUID="$SYSTEM_RANDOM_UUID")

    result = dict([(k, v) for k, v in dummy.setupConfiguration(
        config_dict=special_vars, check_cfg=False).items() if k in special_vars])
    import re
    assert re.match('[0-9]{8}$', result['sv_SYSTEM_DATE'])
    assert re.match('[0-9]{8}_[0-9]{6}$', result['sv_SYSTEM_DATETIME'])
    assert re.match('[0-9]{9,}$', result['sv_SYSTEM_TIMESTAMP'])
    assert re.match('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
                             result['sv_SYSTEM_RANDOM_UUID'])

def test_compose_command():

    from evaluation_system.tests.mocks.dummy import DummyPlugin
    dummy_plugin = DummyPlugin()
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    command = dummy_plugin.composeCommand(config_dict={'the_number': 22},
                                        caption='This is the caption')
    assert similar_string(command, \
        'freva --plugin DummyPlugin --batchmode=False --caption \'This is the caption\' --unique_output True the_number=22 something=test other=1.4')

def test_write_slurm_field(dummy_settings_single):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    from evaluation_system.tests.mocks.dummy import DummyPlugin
    dummy_plugin = DummyPlugin()
    fp = open('/tmp/slurm_test.sh', 'w')
    slurm_file = dummy_plugin.writeSlurmFile(
        fp, config_dict={'the_number': 22}
    )
    fp.close()
    assert os.path.isfile('/tmp/slurm_test.sh')
    assert slurm_file._cmdstring == \
        dummy_plugin.composeCommand(config_dict={'the_number': 22})

def test_suggest_slurm_file_name(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    dummy_plugin.rowid = 1
    fn = dummy_plugin.suggestSlurmFileName()
    date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    assert 'DummyPlugin' in fn
    assert date_str in fn

def test_append_unique_output():
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    from evaluation_system.misc import config
    from evaluation_system.tests.mocks.dummy import DummyPlugin

    try:
        dummy_plugin = DummyPlugin()
        config._config[config.DIRECTORY_STRUCTURE_TYPE] = 'scratch'
        config_dict = {'the_number': 42, 'input': '/my/input/dir',
                       'directory_structure_type': 'scratch'}
        dummy_plugin.rowid = 1
        new_config = dummy_plugin.append_unique_id(config_dict.copy(), True)
        assert new_config['input'] == '/my/input/dir/1'
        new_config = dummy_plugin.append_unique_id(config_dict.copy(), False)
        assert new_config['input'] == '/my/input/dir'
    finally:
        config._config[config.DIRECTORY_STRUCTURE_TYPE] = 'local'
        config.reloadConfiguration()
def test_run_tool(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    result = dummy_plugin._runTool({'the_answer': 42})
    assert result == {'/tmp/dummyfile1': dict(type='plot'),
                              '/tmp/dummyfile2': dict(type='data')}

def test_prepare_output(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    fn = Path(__file__).absolute().parent / 'test_output' / 'vecap_test_output.pdf'
    types_to_check = [
        {'suffix': '.jpg', 'type': 'plot', 'todo': 'copy'},
        {'suffix': '.eps', 'type': 'plot', 'todo': 'convert'},
        {'suffix': '.zip', 'type': 'pdf', 'todo': 'copy'},
        {'suffix': '.pdf', 'type': 'pdf', 'todo': 'copy',
         'fn': fn}
    ]
    for check in types_to_check:
        from evaluation_system.tests.mocks.result_tags import ResultTagTest
        plugin = ResultTagTest()
        if check['suffix'] == '.pdf':
            fn = check.pop('fn')
            meta_data = plugin._runTool({'input': str(fn)})
            meta_data = meta_data[list(meta_data.keys())[0]]
        else:
            with NamedTemporaryFile(mode='wb', suffix=check['suffix']) as fn:
                meta_data = plugin._runTool({'input': fn.name})[fn.name]
        assert meta_data['todo'] == check['todo']
        assert meta_data['type'] == check['type']
        assert meta_data['caption'] == 'Manually added result'
    meta_data = plugin._runTool({'folder':str(fn.parent)})
    assert len(meta_data) == 2

def test_call(dummy_plugin):
    from evaluation_system.api.parameters import (ParameterDictionary,
                                                  Integer, String, Directory)
    res = dummy_plugin.call('echo /bin/bash').strip('\n')
    assert res == '/bin/bash'

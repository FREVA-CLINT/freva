"""
Created on 13.05.2016

@author: Sebastian Illing
"""
import unittest
from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.api.parameters import ParameterDictionary, String, Integer, Float,\
    Bool, Directory, ValidationError

from evaluation_system.tests.mocks.dummy import DummyPlugin, DummyUser
from evaluation_system.tests.mocks.result_tags import ResultTagTest
import os
import datetime
import tempfile


class Test(unittest.TestCase):
    
    def setUp(self):
        self.dummy = DummyPlugin()

    def test_incomplete_abstract(self):
        # this is an incomplete class not implementing all required fields
        class Incomplete(PluginAbstract):
            pass
        self.failUnlessRaises(TypeError, Incomplete)
        
    def test_complete_abstract(self):
        """Tests the creation of a complete implementation of the Plugin Abstract class"""
        # even though py it's just a stub, it should be complete.
        DummyPlugin()
        
    def test_setup_configuration(self):
        user = DummyUser(random_home=True)
        dummy = DummyPlugin(user=user)
        dummy.__parameters__ = ParameterDictionary(String(name='a',
                                                          mandatory=True))
        
        # the default behavior is to check for None values and fail if found
        self.failUnlessRaises(ValidationError, dummy.setupConfiguration)
        
        # it can be turned off
        res = dummy.setupConfiguration(check_cfg=False)
        self.assertEquals(res, {'a': None})

        # check template
        res = dummy.setupConfiguration(dict(num=1), check_cfg=False)
        self.assertEquals(1, res['num'])
        
        # check indirect resolution
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),
                                       check_cfg=False)
        self.assertEquals("1x", res['num'])
        
        # check indirect resolution can also be turned off
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),
                                       check_cfg=False, recursion=False)
        self.assertEquals("${a}x", res['num'])
        
        # check user special values work
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),
                                       check_cfg=False)
        self.assertEquals(user.getUserBaseDir(), res['num'])
        
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),
                                       check_cfg=False, substitute=False)
        self.assertEquals('$USER_BASE_DIR', res['num'])
        
        user.cleanRandomHome()
          
    def test_parse_arguments(self):
        dummy = self.dummy
        dummy.__parameters__ = ParameterDictionary(String(name='a'),
                                                   String(name='b'))
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a='1', b='2'))
        
        dummy.__parameters__ = ParameterDictionary(
                Integer(name='a', default=0),
                Integer(name='b', default=0)
        )
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        
        # even if the default value is different, the metadata can define the type
        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', default='1'), Integer(name='b', default=2)
        )
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        # more arguments than those expected
        dummy.__parameters__ = ParameterDictionary(Integer(name='a',
                                                           default='1'))
        self.failUnlessRaises(ValidationError,
                              dummy.__parameters__.parseArguments,
                              "a=1 b=2".split())
        
        dummy.__parameters__ = ParameterDictionary(Bool(name='a'))
        for arg, parsed_val in [("a=1", True), ("a=true", True), ("a=TRUE", True),
                                ("a=0", False), ("a=false", False),
                                ("a=False", False)]:
            res = dummy.__parameters__.parseArguments(arg.split())
            self.assertEqual(res, dict(a=parsed_val),
                             'Error when parsing %s, got %s' % (arg, res))
        
    def test_parse_metadict(self):
        dummy = self.dummy
        for d, res_d in [(Integer(name='a', default=0), 1),
                         (Integer(name='a'), 1),
                         (Integer(name='a', default='0'), 1),
                         (String(name='a'), '1'),
                         (String(name='a', default=1), '1'),
                         (Bool(name='a'), True),
                         (Float(name='a'), float('1'))]:
            dummy.__parameters__ = ParameterDictionary(d)
            res = dummy._parseConfigStrValue('a', '1')
            self.assertEqual(res, res_d)

        # check errors
        # Wrong type
        dummy.__parameters__ = ParameterDictionary(Integer(name='a'))
        self.failUnlessRaises(ValidationError,
                              dummy._parseConfigStrValue, 'a', 'd')
        # wrong key
        self.failUnlessRaises(ValidationError,
                              dummy._parseConfigStrValue, 'b', '1')
    
    def test_read_config_parser(self):
        from ConfigParser import SafeConfigParser
        from StringIO import StringIO
        conf = SafeConfigParser()
        conf_str = "[DummyPlugin]\na=42\nb=text"
        conf.readfp(StringIO(conf_str))
        dummy = self.dummy
        
        # check parsing
        for d, res_d in [([Integer(name='a')], dict(a=42)),
                         ([String(name='a')], dict(a='42')),
                         ([Integer(name='a'), String(name='b')],
                          dict(a=42, b='text'))]:
            dummy.__parameters__ = ParameterDictionary(*d)
            res = dummy.readFromConfigParser(conf)
            self.assertEqual(res, res_d)
        
        # check errors
        # wrong type
        dummy.__parameters__ = ParameterDictionary(Integer(name='b'))
        self.failUnlessRaises(ValidationError,
                              dummy.readFromConfigParser, conf)
        # wrong regex
        dummy.__parameters__ = ParameterDictionary(Integer(name='a',
                                                           regex='14[0-9]*'))
        self.failUnlessRaises(ValidationError,
                              dummy.readFromConfigParser, conf)
        
    def test_save_config(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = self.dummy
        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', help=''), Integer(name='b', help='')
        )
        tests = [(dict(a=1), '[DummyPlugin]\na=1'),
                 (dict(a='1'), '[DummyPlugin]\na=1'),
                 (dict(b=2), '[DummyPlugin]\nb=2')]
        for t, res in tests:
            res_str.truncate(0)
            dummy.saveConfiguration(res_str, t)
            self.assertEqual(res_str.getvalue().strip(), res)

        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', help='This is \na test'),
            Integer(name='b', help='Also\na\ntest.')
        )
        
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, {'a': 1})
        self.assertEqual(res_str.getvalue().strip(),
                         '[DummyPlugin]\n#: This is\n#: a test\na=1')
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, {'a': 1}, include_defaults=True)
        self.assertEqual(res_str.getvalue().strip(),
                         '[DummyPlugin]\n#: This is\n#: a test\na=1\n\n#: Also\n#: a\n#: test.\n#b=None')

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
        print res_str.getvalue()
        
    def test_read_config(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = self.dummy
        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a'),
            String(name='b', default='test'),
            Float(name='other', default=1.4)
        )
        
        for resource, expected_dict in [('[DummyPlugin]\na=1',
                                         dict(a=1, b='test', other=1.4)),
                                        ('[DummyPlugin]\na=  1   \n', dict(a=1, b='test',
                                                                          other=1.4)),
                                        ('[DummyPlugin]\na=1\nb=2', dict(a=1, b="2",
                                                                        other=1.4)),
                                        ('[DummyPlugin]\n#a=1\nb=2\n#asd\nother=1e10',
                                        dict(a=None, b="2", other=1e10)),
                                        ('[DummyPlugin]\na=-2\nb=blah blah blah',
                                        dict(a=-2, b="blah blah blah", other=1.4))]:
            res_str.truncate(0)
            res_str.write(resource)
            res_str.seek(0)
            
            conf_dict = dummy.readConfiguration(res_str)
            self.assertEqual(conf_dict, expected_dict)
    
    def testSubstitution(self):
        dummy = self.dummy
        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a'), String(name='b', default='value:$a'),
            Directory(name='c', default='$USER_OUTPUT_DIR'))
        
        cfg_str = dummy.getCurrentConfig({'a': 72})
        self.assertTrue('value:72' in cfg_str)
        self.assertTrue(cfg_str.startswith("""a: 72
b: - (default: value:$a [value:72])
c: - (default: $USER_OUTPUT_DIR ["""))

    def test_help(self):
        dummy = self.dummy
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
            self.assertEquals(dummy.getHelp().strip(), resource.strip())
        
    def test_show_config(self):
        user = DummyUser(random_home=True)
        dummy = DummyPlugin(user=user)

        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', mandatory=True, help='This is the value of a'),
            String(name='b', default='test', help='This is not the value of b'),
            Float(name='other', default=1.4, )
        )
        self.assertEquals(dummy.getCurrentConfig(), "    a: - *MUST BE DEFINED!*\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a='/tmp$USER_PLOTS_DIR')), "    a: /tmp$USER_PLOTS_DIR [/tmp" + 
                          user.getUserPlotsDir('DummyPlugin') + "]\n    b: - (default: test)\nother: - (default: 1.4)")

        user.cleanRandomHome()

    def test_usage(self):
        dummy = self.dummy
        dummy.__parameters__ = ParameterDictionary(
            Integer(name='a', help='This is very important'),
            Integer(name='b', default=2),
            String(name='c', help='Well this is just an x...'))
        def_config = dummy.setupConfiguration(check_cfg=False)
        from StringIO import StringIO
        resource = StringIO() 
        dummy.saveConfiguration(resource, def_config)
        res_str1 = resource.getvalue()
        resource.truncate(0)
        dummy.saveConfiguration(resource)
        res_str2 = resource.getvalue()
        self.assertEquals(res_str1, res_str2)
        
    def test_run(self):
        dummy = self.dummy
        # no config
        dummy.runTool()
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue(run is None)
        DummyPlugin._runs = []
        
        # direct config
        dummy.runTool(config_dict=dict(the_number=42))
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 42)
        DummyPlugin._runs = []
        
    def test_get_class_base_dir(self):
        dummy = self.dummy
        import evaluation_system.tests.mocks
        import os
        import re
        self.assertTrue(evaluation_system.tests.\
                        mocks.dummy.__file__.startswith(dummy.getClassBaseDir()))
        # module name should be getClassBaseDir() + modulename_with_"/"_instead_of_"." + ".pyc" or ".py"
        module_name = os.path.abspath(evaluation_system.tests.\
                                      mocks.dummy.__file__)[len(dummy.getClassBaseDir())+1:].replace('/', '.')
        module_name = re.sub("\.pyc?$", "", module_name)
        self.assertEquals(module_name, 'evaluation_system.tests.mocks.dummy')
        
    def test_special_variables(self):
        dummy = self.dummy
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
        print '\n'.join(['%s=%s' % (k, v) for k, v in result.items()])
        import re
        self.assertTrue(re.match('[0-9]{8}$', result['sv_SYSTEM_DATE']))
        self.assertTrue(re.match('[0-9]{8}_[0-9]{6}$', result['sv_SYSTEM_DATETIME']))
        self.assertTrue(re.match('[0-9]{9,}$', result['sv_SYSTEM_TIMESTAMP']))
        self.assertTrue(re.match('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
                                 result['sv_SYSTEM_RANDOM_UUID']))
        
    def test_compose_command(self):
        command = self.dummy.composeCommand(config_dict={'the_number': 22},
                                            caption='This is the caption')
        self.assertEqual(
            command,
            'freva --plugin DummyPlugin --batchmode=False --caption \'This is the caption\' --unique_output True the_number=22 something=test other=1.4'
        )
    
    def test_write_slurm_field(self):
        fp = open('/tmp/slurm_test.sh', 'w')
        slurm_file = self.dummy.writeSlurmFile(
            fp, config_dict={'the_number': 22}
        )
        fp.close()
        self.assertTrue(os.path.isfile('/tmp/slurm_test.sh'))
        self.assertEqual(
            slurm_file._cmdstring,
            self.dummy.composeCommand(config_dict={'the_number': 22})
        )
        
    def test_suggest_slurm_file_name(self):
        fn = self.dummy.suggestSlurmFileName()
        date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        self.assertIn('DummyPlugin', fn)
        self.assertIn(date_str, fn)
    
    def test_append_unique_output(self):
        
        config_dict = {'the_number': 42, 'input': '/my/input/dir'}
        self.dummy.rowid = 1
        new_config = self.dummy.append_unique_id(config_dict.copy(), True)
        self.assertEqual(new_config['input'], '/my/input/dir/1')
        new_config = self.dummy.append_unique_id(config_dict.copy(), False)
        self.assertEqual(new_config['input'], '/my/input/dir')

    def test_run_tool(self):        
        result = self.dummy._runTool({'the_answer': 42})
        self.assertEqual(result, {'/tmp/dummyfile1': dict(type='plot'),
                                  '/tmp/dummyfile2': dict(type='data')})

    def test_prepare_output(self):

        types_to_check = [
            {'suffix': '.jpg', 'type': 'plot', 'todo': 'copy'},
            {'suffix': '.eps', 'type': 'plot', 'todo': 'convert'},
            {'suffix': '.zip', 'type': 'pdf', 'todo': 'copy'},
            {'suffix': '.pdf', 'type': 'pdf', 'todo': 'copy',
             'fn': 'tests/test_output/vecap_test_output.pdf'}
        ]
        for check in types_to_check:
            plugin = ResultTagTest()
            if check['suffix'] == '.pdf':
                meta_data = plugin._runTool({'input': check['fn']})
                meta_data = meta_data[meta_data.keys()[0]]
                print meta_data
            else:
                with tempfile.NamedTemporaryFile(mode='wb', suffix=check['suffix']) as fn:    
                    meta_data = plugin._runTool({'input': fn.name})[fn.name]
            print meta_data, check
            self.assertEqual(meta_data['caption'], 'Manually added result')
            self.assertEqual(meta_data['todo'], check['todo'])
            self.assertEqual(meta_data['type'], check['type'])

        meta_data = plugin._runTool({'folder': 'tests/test_output'})
        self.assertEqual(len(meta_data), 2)

    def test_call(self):
        self.dummy.call('echo $0')   # should print out '/bin/bash

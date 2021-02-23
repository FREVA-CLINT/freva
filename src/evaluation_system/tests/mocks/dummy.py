
import tempfile
import shutil
import os

from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.api.parameters import (ParameterDictionary, Integer, 
    Float, String, Directory)

from evaluation_system.model.user import User
from evaluation_system.model.db import UserDB


class DummyPlugin(PluginAbstract):
    """Stub class for implementing the abstract one"""
    __short_description__ = 'A dummy plugin'
    __version__ = (0,0,0)
    __parameters__ =  ParameterDictionary(
                                   Integer(name='number', help='This is just a number, not really important'),
                                   Integer(name='the_number',mandatory=True,help='This is *THE* number. Please provide it'), 
                                   String(name='something',default='test'),
                                   Float(name='other',default=1.4),
                                   Directory(name='input'))
    _runs = []
    _template = "${number} - $something - $other"

    def runTool(self, config_dict=None):
        DummyPlugin._runs.append(config_dict)
        print(f"Dummy tool was run with: {config_dict}")
        return {'/tmp/dummyfile1': dict(type='plot'), '/tmp/dummyfile2': dict(type='data')}


class DummyUser(User):
    """Create a dummy User object that allows testing"""

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._random_home:
            self.cleanRandomHome()
        return True

    def __init__(self, random_home=False, uid=None, **override):
        self._random_home = None
        if random_home:
            if 'pw_dir' in override:
                raise Exception("Can't define random_home and provide a home directory")
            override['pw_dir'] = tempfile.mkdtemp('_dummyUser')
            self._random_home = override['pw_dir'] 
        super().__init__(uid=uid)
        class DummyUserData(list):
            """Override a normal list and make it work like the pwd read-only struct"""
            _NAMES = 'pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell'.split()

            def __init__(self, arr_list):
                list.__init__(self, arr_list)

            def __getattribute__(self, name):
                # don't access any internal variable (avoid recursion!)
                if name[0] != '_' and name in self._NAMES:
                    return self[self._NAMES.index(name)]
                return list.__getattribute__(self, name)
        # copy the current data
        user_data = list(self._userdata[:])
        for key, value in override.items():
            if key in DummyUserData._NAMES:
                user_data[DummyUserData._NAMES.index(key)] = value
        self._userdata = DummyUserData(user_data)
        self._db = UserDB(self)


    def cleanRandomHome(self):
        try:
            # make sure the home is a temporary one!!!
            shutil.rmtree(self._random_home)
        except (FileNotFoundError, OSError):
            pass

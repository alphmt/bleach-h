# vim: ts=4:sw=4:expandtab

## BleachBit
## Copyright (C) 2009 Andrew Ziem
## http://bleachbit.sourceforge.net
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.



"""
Actions that perform cleaning
"""



import glob
import os
import re
import types
import unittest
import Command
import FileUtilities
import General

if 'posix' == os.name:
    import Unix



###
### Plugin framework
### http://martyalchin.com/2008/jan/10/simple-plugin-framework/
###

class PluginMount(type):
    """A simple plugin framework"""


    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            cls.plugins = []
        else:
            cls.plugins.append(cls)



class ActionProvider:
    """Abstract base class for performing individual cleaning actions"""
    __metaclass__ = PluginMount


    def __init__(self, action_node):
        """Create ActionProvider from CleanerML <action>"""
        pass


    def get_deep_scan(self):
        """Return a dictionary used to construct a deep scan"""
        raise StopIteration

    def get_commands(self):
        """Yield each command (which can be previewed or executed)"""
        pass



###
### base class
###


class FileActionProvider(ActionProvider):
    """Base class for providers which work on individual files"""
    action_key = '_file'

    def __init__(self, action_element):
        """Initialize file search"""
        self.regex = action_element.getAttribute('regex')
        assert(isinstance(self.regex, (str, unicode, types.NoneType)))
        self.search = action_element.getAttribute('search')
        self.path = os.path.expanduser(os.path.expandvars( \
        action_element.getAttribute('path')))
        self.ds = {}
        if 'deep' == self.search:
            self.ds['regex'] = self.regex
            self.ds['cache'] = General.boolstr_to_bool(action_element.getAttribute('cache'))
            self.ds['command'] = action_element.getAttribute('command')
            self.ds['path'] = self.path


    def get_deep_scan(self):
        if 0 == len(self.ds):
            raise StopIteration
        yield self.ds


    def get_paths(self):
        """Return a filtered list of files"""

        def get_file(path):
            if os.path.lexists(path):
                yield path

        def get_walk_all(top):
            for path in FileUtilities.children_in_directory(top, True):
                yield path

        def get_walk_files(top):
            for path in FileUtilities.children_in_directory(top, False):
                yield path

        if 'deep' == self.search:
            raise StopIteration
        elif 'file' == self.search:
            func = get_file
        elif 'glob' == self.search:
            func = glob.iglob
        elif 'walk.all' == self.search:
            func = get_walk_all
        elif 'walk.files' == self.search:
            func = get_walk_files
        else:
            raise RuntimeError("invalid search='%s'" % self.search)

        if None == self.regex:
            for path in func(self.path):
                yield path
        else:
            for path in func(self.path):
                if re.search(self.regex, os.path.basename(path)):
                    yield path


    def get_commands(self):
        raise NotImplementedError('not implemented')


###
### Action providers
###


class AptAutoclean(ActionProvider):
    """Action to run 'apt-get autoclean'"""
    action_key = 'apt.autoclean'


    def __init__(self, action_element):
        pass


    def get_commands(self):
        # Checking executable allows auto-hide to work for non-APT systems
        if FileUtilities.exe_exists('apt-get'):
            yield Command.Function(None, \
                Unix.apt_autoclean, \
                'apt-get autoclean')


class AptAutoremove(ActionProvider):
    """Action to run 'apt-get autoremove'"""
    action_key = 'apt.autoremove'


    def __init__(self, action_element):
        pass

    def get_commands(self):
        # Checking executable allows auto-hide to work for non-APT systems
        if FileUtilities.exe_exists('apt-get'):
            yield Command.Function(None, \
                Unix.apt_autoremove, \
                'apt-get autoremove')


class Delete(FileActionProvider):
    """Action to delete files"""
    action_key = 'delete'


    def get_commands(self):
        for path in self.get_paths():
            yield Command.Delete(path)



class Shred(FileActionProvider):
    """Action to shred files (override preference)"""
    action_key = 'shred'


    def get_commands(self):
        for path in self.get_paths():
            yield Command.Shred(path)



class SqliteVacuum(FileActionProvider):
    """Action to vacuum SQLite databases"""
    action_key = 'sqlite.vacuum'

    def get_commands(self):
        for path in self.get_paths():
            yield Command.Function( \
                path, \
                FileUtilities.vacuum_sqlite3, \
                # TRANSLATORS: Vacuum is a verb.  The term is jargon
                # from the SQLite database.  Microsoft Access uses
                # the term 'Compact Database' (which you may translate
                # instead).  Another synonym is 'defragment.'
               _('Vacuum'))



class Truncate(FileActionProvider):
    """Action to truncate files"""
    action_key = 'truncate'


    def get_commands(self):
        for path in self.get_paths():
            yield Command.Truncate(path)



class TestActionProvider(ActionProvider):
    """Test ActionProvider"""
    action_key = 'test'

    def __init__(self, action_element):
        self.pathname = action_element.getAttribute('path')

    def get_commands(self):
        # non-existent file, should fail and continue
        yield Command.Delete("doesnotexist")

        # access denied, should fail and continue
        def accessdenied():
            raise OSError(13, 'Permission denied: /foo/bar')

        yield Command.Function(None, accessdenied, 'Test access denied')
        # Lock the file on Windows.  It should be marked for deletion.
        if 'nt' == os.name:
            f = os.open(self.pathname, os.O_RDWR | os.O_EXCL)
            yield Command.Delete(self.pathname)
            assert(os.path.exists(self.pathname))
            os.close(f)

        # function with path, should succeed
        def pathfunc(path):
            pass
        # self.pathname must exist because it checks the file size
        yield Command.Function(self.pathname, pathfunc, 'pathfunc')

        # function generator without path, should succeed
        def funcgenerator():
            yield long(10)
        yield Command.Function(None, funcgenerator, 'funcgenerator')

        # plain function without path, should succeed
        def intfunc():
            return int(10)
        yield Command.Function(None, intfunc, 'intfunc')

        # truncate real file
        yield Command.Truncate(self.pathname)

        # real file, should succeed
        yield Command.Delete(self.pathname)

        # file with invalid encoding
        import tempfile
        (fd, filename) = tempfile.mkstemp('invalid-encoding-\xe4\xf6\xfc~')
        os.close(fd)
        yield Command.Delete(filename)


class Winreg(ActionProvider):
    """Action to clean the Windows Registry"""
    action_key = 'winreg'

    def __init__(self, action_element):
        self.keyname = action_element.getAttribute('path')
        self.name = action_element.getAttribute('name')


    def get_commands(self):
        yield Command.Winreg(self.keyname, self.name)



class YumCleanAll(ActionProvider):
    """Action to run 'yum clean all'"""
    action_key = 'yum.clean_all'


    def __init__(self, action_element):
        pass

    def get_commands(self):
        # Checking allows auto-hide to work for non-APT systems
        if not FileUtilities.exe_exists('yum'):
            raise StopIteration

        yield Command.Function( \
                None, \
                Unix.yum_clean, \
                'yum clean all')



class TestAction(unittest.TestCase):
    """Test cases for Action"""


    def _action_str_to_commands(self, action_str):
        """Parse <action> and return commands"""
        from xml.dom.minidom import parseString
        dom = parseString(action_str)
        action_node = dom.childNodes[0]
        delete = Delete(action_node)
        for cmd in delete.get_commands():
            yield cmd


    def _action_str_to_result(self, action_str):
        """Parse <action> and return result"""
        cmd = self._action_str_to_commands(action_str).next()
        result = cmd.execute(False).next()
        return result


    def _test_action_str(self, action_str):
        """Parse <action> and test it"""
        from xml.dom.minidom import parseString
        import Cleaner
        dom = parseString(action_str)
        action_node = dom.childNodes[0]
        command = action_node.getAttribute('command')
        filename = action_node.getAttribute('path')
        provider = None
        for actionplugin in ActionProvider.plugins:
            if actionplugin.action_key == command:
                provider = actionplugin(action_node)
        self.assertNotEqual(provider, None)
        for cmd in provider.get_commands():
            self.assert_(isinstance(cmd, Command.Delete))
            self.assert_(os.path.lexists(filename))
            # preview
            result = cmd.execute(really_delete = False).next()
            Cleaner.TestCleaner.validate_result(self, result)
            self.assertNotEqual('/', result['path'])
            # delete
            result = cmd.execute(really_delete = True).next()
            if 'delete' == command:
                self.assert_(not os.path.lexists(filename))
            elif 'truncate' == command:
                self.assert_(os.path.lexists(filename))
                os.remove(filename)
                self.assert_(not os.path.lexists(filename))
            else:
                raise RuntimeError("Unknown command '%s'" % command)


    def test_delete(self):
        """Unit test for class Delete"""
        import tempfile
        for path in ('~', '$HOME'):
            for command in ('delete', 'truncate'):
                expanded = os.path.expanduser(os.path.expandvars(path))
                (fd, filename) = tempfile.mkstemp(dir = expanded)
                os.close(fd)
                action_str = '<action command="%s" search="file" path="%s" />' % \
                    (command, filename)
                self._test_action_str(action_str)


    def test_regex(self):
        """Unit test for regex option"""
        _iglob = glob.iglob
        glob.iglob = lambda x: ['/tmp/foo1', '/tmp/foo2']
        FileUtilities.getsize = lambda x: 1
        # return regex match
        action_str = '<action command="delete" search="glob" path="/tmp/foo" regex="^foo2$"/>'
        result = self._action_str_to_result(action_str)
        self.assert_(result['path'], '/tmp/foo2')
        # return nothing
        action_str = '<action command="delete" search="glob" path="/tmp/foo" regex="^bar$"/>'
        self.assertRaises(StopIteration, lambda : self._action_str_to_result(action_str))
        # expect error
        action_str = '<action command="delete" search="invalid" path="/tmp/foo" regex="^bar$"/>'
        self.assertRaises(RuntimeError, lambda : self._action_str_to_result(action_str))
        # clean up
        glob.iglob = _iglob


    def test_walk_files(self):
        """Unit test for walk.files"""
        import Cleaner
        if 'posix' == os.name:
            path = '/var'
        elif 'nt' == os.name:
            path = '$WINDIR'
        action_str = '<action command="delete" search="walk.files" path="%s" />' % path
        results = 0
        for cmd in self._action_str_to_commands(action_str):
            result = cmd.execute(False).next()
            Cleaner.TestCleaner.validate_result(self, result)
            path = result['path']
            self.assert_(not os.path.isdir(path), \
                "%s is a directory" % path)
            results += 1
        self.assert_(results > 0)



if __name__ == '__main__':
    unittest.main()


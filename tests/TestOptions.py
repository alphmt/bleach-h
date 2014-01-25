# vim: ts=4:sw=4:expandtab

## BleachBit
## Copyright (C) 2014 Andrew Ziem
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
Test case for module Options
"""


import os
import sys
import unittest
import ConfigParser

sys.path.append('.')
import bleachbit.Options



class OptionsTestCase(unittest.TestCase):
    """Test case for class Options"""

    def test_Options(self):
        """Unit test for class Options"""
        o = bleachbit.Options.options
        value = o.get("check_online_updates")

        # toggle a boolean
        o.toggle('check_online_updates')
        self.assertEqual(not value, o.get("check_online_updates"))

        # restore original boolean
        o.set("check_online_updates", value)
        self.assertEqual(value, o.get("check_online_updates"))

        # test auto commit
        shred = o.get("shred")
        o.set("shred", False)
        self.assertFalse(o.get("shred"))
        o.set("shred", True, commit = False)
        self.assertTrue(o.get("shred"))
        o.restore()
        self.assertFalse(o.get("shred"))
        o.set("shred", shred)
        self.assertEqual(o.get("shred"), shred)

        # try a list
        list_values = ['a', 'b', 'c']
        o.set_list("list_test", list_values)
        self.assertEqual(list_values, o.get_list("list_test"))

        # whitelist
        self.assert_(type(o.get_whitelist_paths() is list))
        whitelist = [ ('file', '/home/foo'), ('folder', '/home') ]
        old_whitelist = o.get_whitelist_paths()
        o.config.remove_section('whitelist/paths')
        self.assert_(type(o.get_whitelist_paths() is list))
        self.assertEqual(o.get_whitelist_paths(), [])
        o.set_whitelist_paths(whitelist)
        self.assert_(type(o.get_whitelist_paths() is list))
        self.assertEqual(set(whitelist), set(o.get_whitelist_paths()))
        o.set_whitelist_paths(old_whitelist)
        self.assertEqual(set(old_whitelist), set(o.get_whitelist_paths()))

        # these should always be set
        for bkey in bleachbit.Options.boolean_keys:
            self.assert_(type(o.get(bkey)) is bool)

        # language
        value = o.get_language('en')
        self.assert_(type(value) is bool)
        o.set_language('en', True)
        self.assertTrue(o.get_language('en'))
        o.set_language('en', False)
        self.assertFalse(o.get_language('en'))
        o.set_language('en', value)

        # tree
        o.set_tree("parent", "child", True)
        self.assertTrue(o.get_tree("parent", "child"))
        o.set_tree("parent", "child", False)
        self.assertFalse(o.get_tree("parent", "child"))
        o.config.remove_option("tree", "parent.child")
        self.assertFalse(o.get_tree("parent", "child"))


    def test_purge(self):
        """Test purging"""
        # By default ConfigParser stores keys (the filenames) as lowercase.
        # This needs special consideration when combined with purging.
        o1 = bleachbit.Options.Options()
        import tempfile
        dirname = tempfile.mkdtemp('bleachbit_test_options')
        pathname = os.path.join(dirname, 'foo.xml')
        file(pathname, 'w').write('') # make an empty file
        self.assertTrue(os.path.exists(pathname))
        myhash = '0ABCD'
        o1.set_hashpath(pathname, myhash)
        self.assertEqual(myhash, o1.get_hashpath(pathname))
        if 'nt' == os.name:
            # check case sensitivity
            self.assertEqual(myhash, o1.get_hashpath(pathname.upper()))
        del o1

        # reopen
        o2 = bleachbit.Options.Options()
        # write something, which triggers the purge
        o2.set('dummypath', 'dummyvalue', 'hashpath')
        # verify the path was not purged
        self.assertTrue(os.path.exists(pathname))
        self.assertEqual(myhash, o2.get_hashpath(pathname))

        # delete the path
        os.remove(pathname)
        # close and reopen
        del o2
        o3 = bleachbit.Options.Options()
        # write something, which triggers the purge
        o3.set('dummypath', 'dummyvalue', 'hashpath')
        # verify the path was purged
        self.assertRaises(ConfigParser.NoOptionError, lambda: o3.get_hashpath(pathname))

        # clean up
        os.rmdir(dirname)




def suite():
    return unittest.makeSuite(OptionsTestCase)


if __name__ == '__main__':
    unittest.main()


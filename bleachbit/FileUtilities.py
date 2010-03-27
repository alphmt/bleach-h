# vim: ts=4:sw=4:expandtab
# -*- coding: UTF-8 -*-

## BleachBit
## Copyright (C) 2010 Andrew Ziem
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
File-related utilities
"""



import datetime
import glob
import locale
import os
import re
import stat
import subprocess
import sys
import tempfile

if not "iglob" in dir(glob):
    glob.iglob = glob.glob

from Options import options

if 'posix' == os.name:
    from General import WindowsError



class OpenFiles:
    """Cached way to determine whether a file is open by active process"""
    def __init__(self):
        self.last_scan_time = None
        self.files = []

    def file_qualifies(self, filename):
        """Return boolean wehether filename qualifies to enter cache (check \
        against blacklist)"""
        return not filename.startswith("/dev") and \
            not filename.startswith("/proc")

    def scan(self):
        """Update cache"""
        self.last_scan_time = datetime.datetime.now()
        self.files = []
        for filename in glob.iglob("/proc/*/fd/*"):
            try:
                target = os.path.realpath(filename)
            except TypeError:
                # happens, for example, when link points to
                # '/etc/password\x00 (deleted)'
                continue
            if self.file_qualifies(target):
                self.files.append(target)

    def is_open(self, filename):
        """Return boolean whether filename is open by running process"""
        if None == self.last_scan_time or (datetime.datetime.now() - 
            self.last_scan_time).seconds > 10:
            self.scan()
        return filename in self.files


def bytes_to_human(bytes_i):
    """Display a file size in human terms (megabytes, etc.)"""

    storage_multipliers = { 1024**5 : 'PiB', 1024**4 : 'TiB', \
        1024**3 : 'GiB', 1024**2: 'MiB', 1024: 'KiB', 1 : 'B' }

    assert(isinstance(bytes_i, (int, long)))

    if 0 == bytes_i:
        return "0"

    if bytes_i >= 1024**3:
        decimals = 2
    elif bytes_i >= 1024:
        decimals = 1
    else:
        decimals = 0

    for key in sorted(storage_multipliers.keys(), reverse = True):
        if bytes_i >= key:
            abbrev = round((1.0 * bytes_i) / key, decimals)
            suf = storage_multipliers[key]
            return locale.str(abbrev) + suf

    if bytes_i < 0:
        return "-" + bytes_to_human(abs(bytes_i))


def children_in_directory(top, list_directories = False):
    """Iterate files and, optionally, subdirectories in directory"""
    if type(top) is tuple:
        for top_ in top:
            for pathname in children_in_directory(top_, list_directories):
                yield pathname
        return
    for (dirpath, dirnames, filenames) in os.walk(top, topdown=False):
        if list_directories:
            for dirname in dirnames:
                yield os.path.join(dirpath, dirname)
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def delete(path, shred = False):
    """Delete path that is either file, directory, link or FIFO"""
    try:
        print u"info: removing '%s'" % path
    except:
        # FIXME: unicode exception workaround for Windows (see unit test)
        print "info: removing '%s'" % path.encode('ascii', 'replace')
    mode = os.lstat(path)[stat.ST_MODE]
    if stat.S_ISFIFO(mode) or stat.S_ISLNK(mode):
        os.remove(path)
    elif stat.S_ISDIR(mode):
        try:
            os.rmdir(path)
        except WindowsError, e:
            if 145 == e.winerror:
                print "info: directory '%s' is not empty" % (path)
            else:
                raise
    elif stat.S_ISREG(mode):
        if shred or options.get('shred'):
            try:
                wipe_contents(path)
            except IOError, e:
                # permission denied (13) happens shredding MSIE 8 on Windows 7
                print "debug: IOError #%s shredding '%s'" % (e.errno, path)
        try:
            os.remove(path)
        except WindowsError, e:
            # WindowsError: [Error 145] The directory is not empty:
            # 'C:\\Documents and Settings\\username\\Local Settings\\Temp\\NAILogs'
            # Error 145 may happen if the files are scheduled for deletion
            # during reboot.
            if 145 == e.winerror:
                print "info: directory '%s' is not empty" % (path)
            else:
                raise
    else:
        raise Exception("Unsupported special file type")


def ego_owner(filename):
    """Return whether current user owns the file"""
    return os.lstat(filename).st_uid == os.getuid()


def exists_in_path(filename):
    """Returns boolean whether the filename exists in the path"""
    delimiter = ':'
    if 'nt' == os.name:
        delimiter = ';'
    for dirname in os.getenv('PATH').split(delimiter):
        if os.path.exists(os.path.join(dirname, filename)):
            return True
    return False


def exe_exists(pathname):
    """Returns boolean whether executable exists"""
    if os.path.isabs(pathname):
        if not os.path.exists(pathname):
            return False
    else:
        if not exists_in_path(pathname):
            return False
    return True


def execute_sqlite3(path, cmds):
    """Execute 'cmds' on SQLite database 'path'"""
    try:
        import sqlite3
    except ImportError, exc:
        if sys.version_info[0] == 2 and sys.version_info[1] < 5:
            raise RuntimeError(_("Cannot import Python module sqlite3: Python 2.5 or later is required."))
        else:
            raise exc
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    for cmd in cmds.split(';'):
        try:
            cursor.execute(cmd)
        except sqlite3.OperationalError, exc:
            if exc.message.find('no such function: ') >= 0:
                # fixme: determine why randomblob and zeroblob are not available
                print 'warning: %s' % exc.message
            else:
                raise sqlite3.OperationalError('%s: %s' % (exc, path))
    cursor.close()
    conn.commit()
    conn.close()


def expand_glob_join(pathname1, pathname2):
    """Join pathname1 and pathname1, expand pathname, glob, and return as list"""
    ret = []
    pathname3 = os.path.expanduser(os.path.expandvars(os.path.join(pathname1, pathname2)))
    for pathname4 in glob.iglob(pathname3):
        ret.append(pathname4)
    return ret


def getsize(path):
    """Return the actual file size considering spare files
       and symlinks"""
    if 'posix' == os.name:
        __stat = os.lstat(path)
        return __stat.st_blocks * 512
    return os.path.getsize(path)


def getsizedir(path):
    """Return the size of the contents of a directory"""
    total_bytes = 0
    for node in children_in_directory(path, list_directories = False):
        total_bytes += getsize(node)
    return total_bytes


def globex(pathname, regex):
    """Yield a list of files with pathname and filter by regex"""
    if type(pathname) is tuple:
        for singleglob in pathname:
            for path in globex(singleglob, regex):
                yield path
    else:
        for path in glob.iglob(pathname):
            if re.search(regex, path):
                yield path


def human_to_bytes(string):
    """Convert a string like 10.2GB into bytes"""
    multiplier = { 'B' : 1, 'KB': 1024, 'MB': 1024**2, \
        'GB': 1024**3, 'TB': 1024**4 }
    matches = re.findall("^([0-9]*)(\.[0-9]{1,2})?([KMGT]{0,1}B)$", string)
    if 2 > len(matches[0]):
        raise ValueError("Invalid input for '%s'" % (string))
    return int(float(matches[0][0]+matches[0][1]) * multiplier[matches[0][2]])


def listdir(directory):
    """Return full path of files in directory.

    Path may be a tuple of directories."""

    if type(directory) is tuple:
        for dirname in directory:
            for pathname in listdir(dirname):
                yield pathname
        return
    dirname = os.path.expanduser(directory)
    if not os.path.lexists(dirname):
        return
    for filename in os.listdir(dirname):
        yield os.path.join(dirname, filename)


def wipe_contents(path, truncate = True):
    """Wipe files contents

    http://en.wikipedia.org/wiki/Data_remanence
    2006 NIST Special Publication 800-88 (p. 7): "Studies have
    shown that most of today's media can be effectively cleared
    by one overwrite"
    """
    size = getsize(path)
    try:
        f = open(path, 'wb')
    except IOError, e:
        if 13 == e.errno: # permission denied
            os.chmod(path, 0200) # user write only
            f = open(path, 'wb')
        else:
            raise
    blanks =  chr(0) * 4096
    while size > 0:
        f.write(blanks)
        size -= 4096
    f.flush()
    if truncate:
        f.truncate(0)
        f.flush()
    f.close()


def wipe_path(pathname, idle = False ):
    """Wipe the free space in the path"""
    print "debug: wipe_path('%s')" % pathname
    files = []
    total_bytes = 0
    # repeat to clear inodes (Linux) / MFT (Master File Table on Windows)
    while True:
        try:
            f = tempfile.TemporaryFile(dir = pathname)
        except OSError, e:
            # Linux gives errno 24
            # Windows gives errno 28 No space left on device
            if e.errno in (24, 28):
                break
            else:
                raise
        last_idle = datetime.datetime.now()
        # blocks
        blanks = chr(0) * 4096
        try:
            while True:
                f.write(blanks)
                if idle and (last_idle - datetime.datetime.now()).seconds > 1:
                    # Keep the GUI responding, and allow the user to abort.
                    yield True
        except IOError, e:
            if 28 != e.errno:
                raise
        # individual characters
        try:
            while True:
                f.write(chr(0))
        except IOError, e:
            if 28 != e.errno:
                raise
        try:
            f.flush()
        except:
            # IOError: [Errno 28] No space left on device
            # seen on Microsoft Windows XP SP3 with ~30GB free space but
            # not on another XP SP3 with 64MB free space
            print "info: exception on f.flush()"
        files.append(f)
        total_bytes += f.tell()
    # statistics
    print 'debug: wrote %d files and %d bytes' % (len(files), total_bytes)
    # truncate and close files
    for f in files:
        f.truncate(0)
        f.close()
    # files are removed implicitly


def vacuum_sqlite3(path):
    """Vacuum SQLite database"""
    execute_sqlite3(path, 'vacuum')


openfiles = OpenFiles()




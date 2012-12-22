# vim: ts=4:sw=4:expandtab
# -*- coding: UTF-8 -*-

## BleachBit
## Copyright (C) 2012 Andrew Ziem
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
Wipe memory
"""



import ctypes
import os
import re
import subprocess
import sys
import traceback

import FileUtilities
import General



def count_swap_linux():
    """Count the number of swap devices in use"""
    f = open("/proc/swaps")
    count = 0
    for line in f:
        if line[0] == '/':
            count += 1
    return count


def disable_swap_linux():
    """Disable Linux swap and return list of devices"""
    if 0 == count_swap_linux():
        return
    print "debug: disabling swap"
    args = ["swapoff", "-a", "-v"]
    (rc, stdout, stderr) = General.run_external(args)
    if 0 != rc:
        raise RuntimeError(stderr.replace("\n", ""))
    devices = []
    for line in stdout.split('\n'):
        line = line.replace('\n', '')
        if '' == line:
            continue
        # English is 'swapoff on /dev/sda5' but German is 'swapoff für ...'
        # Example output in English with LVM and hyphen: 'swapoff on /dev/mapper/lubuntu-swap_1'
        # This matches swap devices and swap files
        ret = re.search('^swapoff .* (/[\w/\.-]+)$', line)
        if None == ret:
            raise RuntimeError("Unexpected output:\nargs='%(args)s'\nstdout='%(stdout)s'\nstderr='%(stderr)s'" \
                % { 'args' : str(args), 'stdout' : stdout, 'stderr' : stderr } )
        devices.append(ret.group(1))
    return devices


def enable_swap_linux():
    """Enable Linux swap"""
    print "debug: re-enabling swap"
    args = ["swapon", "-a"]
    p = subprocess.Popen(args, stderr=subprocess.PIPE)
    p.wait()
    outputs = p.communicate()
    if 0 != p.returncode:
        raise RuntimeError(outputs[1].replace("\n", ""))


def fill_memory_linux():
    """Fill unallocated memory"""
    # make self primary target for Linux out-of-memory killer
    path = '/proc/%d/oomadj' % os.getpid()
    if os.path.exists(path):
        f = open(path)
        f.write('15')
        f.close()
    # OOM likes nice processes
    print 'debug: new nice value', os.nice(19)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    # OOM prefers non-privileged processes
    try:
        uid = General.getrealuid()
        if uid > 0:
            print "debug: dropping privileges of pid %d to uid %d" % \
                    (os.getpid(), uid)
            os.seteuid(uid)
    except:
        traceback.print_exc()
    # fill memory
    def fill_helper():
        report_free()
        allocbytes = int(physical_free() * 0.75)
        if allocbytes < 1024:
            return
        megabytes = allocbytes / (1024**2)
        print "info: allocating %.2f MB (%d B) memory" % (megabytes, allocbytes)
        mbuffer = libc.malloc(allocbytes)
        if 0 == mbuffer:
            print 'debug: malloc() returned', mbuffer
            return
        print "debug: wiping %.2f MB I just allocated" % megabytes
        libc.memset(mbuffer, 0x00, allocbytes)
        fill_helper()
        print "debug: freeing %.2f MB memory" % megabytes
        libc.free(mbuffer)
        report_free()
    fill_helper()


def get_swap_size_linux(device, proc_swaps = None):
    """Return the size of the partition in bytes"""
    if None == proc_swaps:
        proc_swaps = open("/proc/swaps").read()
    line = proc_swaps.split('\n')[0]
    if not re.search('Filename\s+Type\s+Size', line):
        raise RuntimeError("Unexpected first line in /proc/swaps '%s'" % line)
    for line in proc_swaps.split('\n')[1:]:
        ret = re.search("%s\s+\w+\s+([0-9]+)\s" % device, line)
        if ret:
            return int(ret.group(1)) * 1024
    raise RuntimeError("error: cannot find size of swap device '%s'\n%s" % \
        (device, proc_swaps))


def get_swap_uuid(device):
    """Find the UUID for the swap device"""
    uuid = None
    args = ['blkid', device, '-s', 'UUID']
    (rc, stdout, stderr) = General.run_external(args)
    for line in stdout.split('\n'):
        # example: /dev/sda5: UUID="ee0e85f6-6e5c-42b9-902f-776531938bbf"
        ret = re.search("^%s: UUID=\"([a-z0-9-]+)\"" % device, line)
        if None != ret:
             uuid = ret.group(1)
    print "debug: uuid(%s)='%s'" % (device, uuid)
    return uuid


def physical_free_linux():
    """Return the physical free memory on Linux"""
    f = open("/proc/meminfo")
    bytes = 0
    for line in f:
        line = line.replace("\n","")
        ret = re.search('(MemFree|Cached):[ ]*([0-9]*) kB', line)
        if None != ret:
            kb = int(ret.group(2))
            bytes += kb * 1024
    if bytes > 0:
        return bytes
    else:
        raise Exception("unknown")


def physical_free_windows():
    """Return physical free memory on Windows"""

    from ctypes import c_long, c_ulonglong
    from ctypes.wintypes import Structure, sizeof, windll, byref

    class MEMORYSTATUSEX(Structure):
        _fields_ = [
            ('dwLength', c_long),
            ('dwMemoryLoad', c_long),
            ('ullTotalPhys', c_ulonglong),
            ('ullAvailPhys', c_ulonglong),
            ('ullTotalPageFile', c_ulonglong),
            ('ullAvailPageFile', c_ulonglong),
            ('ullTotalVirtual', c_ulonglong),
            ('ullAvailVirtual', c_ulonglong),
            ('ullExtendedVirtual', c_ulonglong),
        ]

    def GlobalMemoryStatusEx():
        x = MEMORYSTATUSEX()
        x.dwLength = sizeof(x)
        windll.kernel32.GlobalMemoryStatusEx(byref(x))
        return x

    z = GlobalMemoryStatusEx()
    print z
    return z.ullAvailPhys


def physical_free():
    if sys.platform.startswith('linux'):
        return physical_free_linux()
    elif 'win32' == sys.platform:
        return physical_free_windows()
    else:
        raise RuntimeError('unsupported platform for physical_free()')


def report_free():
    """Report free memory"""
    bytes_free = physical_free()
    print "debug: physical free: %d B (%d MB)" % \
        (bytes_free, bytes_free / 1024**2)


def wipe_swap_linux(devices, proc_swaps):
    """Shred the Linux swap file and then reinitilize it"""
    if None == devices:
        return
    if 0 < count_swap_linux():
        raise RuntimeError('Cannot wipe swap while it is in use')
    for device in devices:
        print "info: wiping swap device '%s'" % device
        if get_swap_size_linux(device, proc_swaps) > 8*1024**3:
            raise RuntimeError('swap device %s is larger than expected' % device)
        uuid = get_swap_uuid(device)
        # wipe
        FileUtilities.wipe_contents(device, truncate = False)
        # reinitialize
        print "debug: reinitializing swap device %s" % device
        args = ['mkswap', device]
        if uuid:
            args.append("-U")
            args.append(uuid)
        (rc, stdout, stderr) = General.run_external(args)
        if 0 != rc:
            raise RuntimeError(stderr.replace("\n", ""))


def wipe_memory():
    """Wipe unallocated memory"""
    # cache the file because 'swapoff' changes it
    proc_swaps = open("/proc/swaps").read()
    devices = disable_swap_linux()
    yield True # process GTK+ idle loop
    print 'debug: detected swap devices:', devices
    wipe_swap_linux(devices, proc_swaps)
    yield True
    child_pid = os.fork()
    if 0 == child_pid:
        fill_memory_linux()
        sys.exit(0)
    else:
        print 'debug: wipe_memory() pid %d waiting for child pid %d' % \
            (os.getpid(), child_pid)
        rc = os.waitpid(child_pid, 0)[1]
        if 0 != rc:
            print 'warning: child process returned code %d' % rc
    enable_swap_linux()
    yield 0 # how much disk space was recovered




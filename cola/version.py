# Copyright (c) 2008 David Aguilar
import re
import os
import sys

from cola.exception import ColaException
from cola import utils

class VersionUnavailable(ColaException):
    pass

def git_describe_version():
    path = sys.path[0]
    try:
        v = utils.run_cmd('git', 'describe', '--tags', '--abbrev=4', 'master')
    except utils.RunCommandException, e:
        raise VersionUnavailable(str(e))
    if not re.match(r'^v[0-9]', v):
        raise VersionUnavailable('%s: bad version' % v)
    try:
        utils.run_cmd('git', 'update-index', '--refresh')
        dirty = utils.run_cmd('git', 'diff-index', '--name-only', 'HEAD')
    except utils.RunCommandException, e:
        raise VersionUnavailable(str(e))
    if dirty:
        v += '-dirty'
    return re.sub('-', '.', utils.strip_prefix('v', v))

def builtin_version():
    try:
        import builtin_version as bv
    except ImportError:
        raise VersionUnavailable()
    else:
        return bv.version

def _builtin_version_file(ext = 'py'):
    return os.path.join(sys.path[0], 'cola', 'builtin_version.%s' % ext)

def write_builtin_version():
    try:
        v = git_describe_version()
    except VersionUnavailable:
        return
    f = file(_builtin_version_file(), 'w')
    f.write('# This file was generated automatically. Do not edit by hand.\n'
            'version = %r\n' % v)

def delete_builtin_version():
    for ext in ['py', 'pyc', 'pyo']:
        fn = _builtin_version_file(ext)
        if os.path.exists(fn):
            os.remove(fn)

def get_version():
    for v in [builtin_version, git_describe_version]:
        try:
            return v()
        except VersionUnavailable:
            pass
    return '1.2'

version = get_version()

# minimum version requirements
git_min_ver = '1.5.2'
python_min_ver = '2.4'
pyqt_min_ver = '4.3'

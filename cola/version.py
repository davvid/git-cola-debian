# Copyright (c) 2008 David Aguilar
"""Provides the current cola version number"""

import re
import os
import sys

from cola import git
from cola import errors
from cola import utils
from cola import resources
from cola.decorators import memoize


# minimum version requirements
_versions = {
    'git': '1.5.2',
    'python': '2.4',
    'pyqt': '4.1',
    'pyqt_qrunnable': '4.4',
    # git-difftool moved out of contrib in git 1.6.3
    'difftool-builtin': '1.6.3',
    # git-mergetool learned --no-prompt in 1.6.2
    'mergetool-no-prompt': '1.6.2',
    'patience': '1.6.2',
    'diff-submodule': '1.6.6',
}


def get(key):
    """Returns an entry from the known versions table"""
    return _versions.get(key)


class VersionUnavailable(Exception):
    pass


def git_describe_version():
    """Inspect the cola git repository and return the current version."""
    try:
        v = git.Git.execute(['git', 'describe',
                            '--tags',
                            '--match=v*',
                            '--abbrev=7',
                            'HEAD'],
                            with_stderr=True)
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if not re.match(r'^v[0-9]', v):
        raise VersionUnavailable('%s: bad version' % v)
    try:
        dirty = git.Git.execute(['git', 'diff-index', '--name-only', 'HEAD'])
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if dirty:
        v += '-dirty'
    return re.sub('-', '.', utils.strip_prefix('v', v))


def builtin_version():
    """Return the builtin version or throw a VersionUnavailable exception"""
    try:
        from cola import builtin_version as bv
    except ImportError, e:
        raise VersionUnavailable()
    else:
        return bv.version


@memoize
def _builtin_version_file(ext='py'):
    """Returns the path to cola's builtin_version.py."""
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, 'builtin_version.%s' % ext)


def write_builtin_version():
    """Writes cola/builtin_version.py."""
    try:
        v = git_describe_version()
    except VersionUnavailable:
        return
    f = file(_builtin_version_file(), 'w')
    f.write('# This file was generated automatically. Do not edit by hand.\n'
            'version = %r\n' % v)

def delete_builtin_version():
    """Deletes cola/builtin_version.py."""
    for ext in ('py', 'pyc', 'pyo'):
        fn = _builtin_version_file(ext=ext)
        if os.path.exists(fn):
            os.remove(fn)


@memoize
def version():
    """Returns the builtin version or calculates the current version."""
    for v in [builtin_version, git_describe_version]:
        try:
            return v()
        except VersionUnavailable:
            pass
    return 'unknown-version'


@memoize
def check_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver
    """
    test = (min_ver, ver)
    min_ver_list = version_to_list(min_ver)
    ver_list = version_to_list(ver)
    return min_ver_list <= ver_list


@memoize
def check(key, ver):
    """Checks if a version is greater than the known version for <what>"""
    return check_version(get(key), ver)


def version_to_list(version):
    """Convert a version string to a list of numbers or strings
    """
    ver_list = []
    for p in version.split('.'):
        try:
            n = int(p)
        except ValueError:
            n = p
        ver_list.append(n)
    return ver_list


@memoize
def git_version():
    """Returns the current GIT version"""
    return git.instance().version().split()[-1]

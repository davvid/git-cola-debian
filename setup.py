#!/usr/bin/env python
import re
import os
import sys
import stat
from glob import glob

from distutils.core import setup
from distutils.command import build_scripts
build_scripts.first_line_re = re.compile('^should not match$')

from cola import version
from cola import utils
from cola import resources
from cola import core

def main():
    # ensure readable files
    old_mask = os.umask(0022)
    git_version = version.get_git_version()
    if sys.argv[1] in ['install', 'build']:
        _setup_environment()
        _check_python_version()
        _check_git_version(git_version)
        _check_pyqt_version()
        _build_views()             # pyuic4: .ui -> .py
        _build_translations()      # msgfmt: .po -> .qm
    try:
        version.write_builtin_version()
        _run_setup(git_version)
    finally:
        version.delete_builtin_version()
    # restore the old mask
    os.umask(old_mask)

def _setup_environment():
    """Adds win32/ to our path for windows only"""
    if sys.platform != 'win32':
        return
    path = os.environ['PATH']
    win32 = os.path.join(os.path.dirname(__file__), 'win32')
    os.environ['PATH'] = win32 + os.pathsep + path

def _run_setup(git_version):
    """Runs distutils.setup()"""

    scripts = ['bin/git-cola']

    # git-difftool first moved out of git.git's contrib area in git 1.6.3
    if (os.environ.get('INSTALL_GIT_DIFFTOOL', '') or
            not version.check('difftool-builtin', git_version)):
        scripts.append('bin/difftool/git-difftool')
        scripts.append('bin/difftool/git-difftool--helper')

    if sys.platform == 'win32':
        scripts.append('win32/cola')
        scripts.append('win32/dirname')
        scripts.append('win32/py2exe-setup.py')
        scripts.append('win32/py2exe-setup.cmd')

    setup(name = 'git-cola',
          version = version.get_version(),
          license = 'GPLv2',
          author = 'David Aguilar and contributors',
          author_email = 'davvid@gmail.com',
          url = 'http://cola.tuxfamily.org/',
          description = 'git-cola',
          long_description = 'A highly caffeinated git gui',
          scripts = scripts,
          packages = [],
          data_files = cola_data_files())


def cola_data_files():
    return [_app_path('share/git-cola/qm', '*.qm'),
            _app_path('share/git-cola/icons', '*.png'),
            _app_path('share/git-cola/icons', '*.svg'),
            _app_path('share/git-cola/styles', '*.qss'),
            _app_path('share/git-cola/styles/images', '*.png'),
            _app_path('share/applications', '*.desktop'),
            _app_path('share/doc/git-cola', '*.txt'),
            _lib_path('cola/*.py'),
            _lib_path('cola/models/*.py'),
            _lib_path('cola/controllers/*.py'),
            _lib_path('cola/gui/*.py'),
            _lib_path('cola/views/*.py'),
            _lib_path('jsonpickle/*.py'),
            _lib_path('simplejson/*.py')]

def _lib_path(entry):
    dirname = os.path.dirname(entry)
    app_dir = os.path.join('share/git-cola/lib', dirname)
    return (app_dir, glob(entry))


def _app_path(dirname, entry):
    return (dirname, glob(os.path.join(dirname, entry)))


def _check_python_version():
    """Check the minimum Python version
    """
    pyver = '.'.join(map(lambda x: str(x), sys.version_info))
    if not version.check('python', pyver):
        print >> sys.stderr, ('Python version %s or newer required.  '
                              'Found %s' % (version.get('python'), pyver))
        sys.exit(1)


def _check_git_version(git_ver):
    """Check the minimum GIT version
    """
    if not version.check('git', git_ver):
        print >> sys.stderr, ('GIT version %s or newer required.  '
                              'Found %s' % (version.get('git'), git_ver))
        sys.exit(1)

def _check_pyqt_version():
    """Check the minimum PyQt version
    """
    failed = False
    try:
        pyqtver = _run_cmd(['pyuic4', '--version']).split()[-1]
    except IndexError:
        pyqtver = 'nothing'
        failed = True
    if failed or not version.check('pyqt', pyqtver):
        print >> sys.stderr, ('PYQT version %s or newer required.  '
                              'Found %s' % (version.get('pyqt'), pyqtver))
        sys.exit(1)


def _dirty(src, dst):
    if not os.path.exists(dst):
        return True
    srcstat = os.stat(src)
    dststat = os.stat(dst)
    return srcstat[stat.ST_MTIME] > dststat[stat.ST_MTIME]


def _workaround_pyuic4(src, dst):
    fh = open(src, 'r')
    contents = core.read_nointr(fh)
    fh.close()
    fh = open(dst, 'w')
    for line in contents.splitlines():
        if 'sortingenabled' in line.lower():
            continue
        core.write_nointr(fh, line+os.linesep)
    fh.close()
    os.unlink(src)


def _build_views():
    print 'running build_views'
    views = os.path.join('cola', 'gui')
    sources = glob('ui/*.ui')
    for src in sources:
        dst = os.path.join(views, os.path.basename(src)[:-3] + '.py')
        dsttmp = dst + '.tmp'
        if _dirty(src, dst):
            print '\tpyuic4 -x %s -o %s' % (src, dsttmp)
            utils.run_cmd('pyuic4', '-x', src, '-o', dsttmp)
            _workaround_pyuic4(dsttmp, dst)


def _build_translations():
    print 'running build_translations'
    sources = glob(resources.share('po', '*.po'))
    sources = glob('share/git-cola/po/*.po')
    for src in sources:
        dst = resources.qm(os.path.basename(src)[:-3])
        if _dirty(src, dst):
            print '\tmsgfmt --qt %s -o %s' % (src, dst)
            utils.run_cmd('msgfmt', '--qt', src, '-o', dst)

def _run_cmd(args):
    """Runs a command and returns its output"""
    argstr = utils.shell_quote(*args)
    pipe = os.popen(argstr)
    contents = core.read_nointr(pipe).strip()
    pipe.close()
    return contents


if __name__ == '__main__':
    main()

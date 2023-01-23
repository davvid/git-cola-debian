import os
import sys
import subprocess
import threading
from os.path import join

from cola import core
from cola.decorators import memoize
from cola.interaction import Interaction


INDEX_LOCK = threading.Lock()
GIT_COLA_TRACE = core.getenv('GIT_COLA_TRACE', '')
STATUS = 0
STDOUT = 1
STDERR = 2


def dashify(s):
    return s.replace('_', '-')


def is_git_dir(d):
    """From git's setup.c:is_git_directory()."""
    if (core.isdir(d) and core.isdir(join(d, 'objects')) and
            core.isdir(join(d, 'refs'))):
        headref = join(d, 'HEAD')
        return (core.isfile(headref) or
                (core.islink(headref) and
                    core.readlink(headref).startswith('refs')))

    return is_git_file(d)


def is_git_file(f):
    return core.isfile(f) and '.git' == os.path.basename(f)


def is_git_worktree(d):
    return is_git_dir(join(d, '.git'))


def read_git_file(path):
    if path is None:
        return None
    if is_git_file(path):
        data = core.read(path).strip()
        if data.startswith('gitdir: '):
            return data[len('gitdir: '):]
    return None


class Git(object):
    """
    The Git class manages communication with the Git binary
    """
    def __init__(self):
        self._git_cwd = None #: The working directory used by execute()
        self._worktree = None
        self._git_file_path = None
        self.set_worktree(core.getcwd())

    def set_worktree(self, path):
        self._git_dir = path
        self._git_file_path = None
        self._worktree = None
        self.worktree()

    def worktree(self):
        if self._worktree:
            return self._worktree
        self.git_dir()
        if self._git_dir:
            curdir = self._git_dir
        else:
            curdir = core.getcwd()

        if is_git_dir(join(curdir, '.git')):
            return curdir

        # Handle bare repositories
        if (len(os.path.basename(curdir)) > 4
                and curdir.endswith('.git')):
            return curdir
        if 'GIT_WORK_TREE' in os.environ:
            self._worktree = core.getenv('GIT_WORK_TREE')
        if not self._worktree or not core.isdir(self._worktree):
            if self._git_dir:
                gitparent = join(core.abspath(self._git_dir), '..')
                self._worktree = core.abspath(gitparent)
                self.set_cwd(self._worktree)
        return self._worktree

    def is_valid(self):
        return self._git_dir and is_git_dir(self._git_dir)

    def git_path(self, *paths):
        if self._git_file_path is None:
            return join(self.git_dir(), *paths)
        else:
            return join(self._git_file_path, *paths)

    def git_dir(self):
        if self.is_valid():
            return self._git_dir
        if 'GIT_DIR' in os.environ:
            self._git_dir = core.getenv('GIT_DIR')
        if self._git_dir:
            curpath = core.abspath(self._git_dir)
        else:
            curpath = core.abspath(core.getcwd())
        # Search for a .git directory
        while curpath:
            if is_git_dir(curpath):
                self._git_dir = curpath
                break
            gitpath = join(curpath, '.git')
            if is_git_dir(gitpath):
                self._git_dir = gitpath
                break
            curpath, dummy = os.path.split(curpath)
            if not dummy:
                break
        self._git_file_path = read_git_file(self._git_dir)
        return self._git_dir

    def set_cwd(self, path):
        """Sets the current directory."""
        self._git_cwd = path

    def __getattr__(self, name):
        if name[:1] == '_':
            raise AttributeError(name)
        return lambda *args, **kwargs: self._call_process(name, *args, **kwargs)

    @staticmethod
    def execute(command,
                _cwd=None,
                _stdin=None,
                _raw=False,
                _decode=True,
                _encoding=None):
        """
        Execute a command and returns its output

        :param command: argument list to execute.
        :param _cwd: working directory, defaults to the current directory.
        :param _decode: whether to decode output, defaults to True.
        :param _encoding: default encoding, defaults to None (utf-8).
        :param _raw: do not strip trailing whitespace.
        :param _stdin: optional stdin filehandle.
        :returns (status, out, err): exit status, stdout, stderr

        """
        # Allow the user to have the command executed in their working dir.
        if not _cwd:
            _cwd = core.getcwd()

        extra = {}
        if sys.platform == 'win32':
            command = map(replace_carot, command)
            extra['shell'] = True

        # Start the process
        # Guard against thread-unsafe .git/index.lock files
        INDEX_LOCK.acquire()
        status, out, err = core.run_command(command,
                                            cwd=_cwd, stdin=_stdin, **extra)
        # Let the next thread in
        INDEX_LOCK.release()
        if _decode:
            out = core.decode(out, encoding=_encoding)
            err = core.decode(err, encoding=_encoding)
        if not _raw:
            out = out.rstrip('\n')

        cola_trace = GIT_COLA_TRACE
        if cola_trace == 'trace':
            msg = 'trace: ' + subprocess.list2cmdline(command)
            Interaction.log_status(status, msg, '')
        elif cola_trace == 'full':
            if out:
                core.stderr("%s -> %d: '%s' '%s'" %
                            (' '.join(command), status, out, err))
            else:
                core.stderr("%s -> %d" % (' '.join(command), status))
        elif cola_trace:
            core.stderr(' '.join(command))

        # Allow access to the command's status code
        return (status, out, err)

    def transform_kwargs(self, **kwargs):
        """Transform kwargs into git command line options"""
        args = []
        for k, v in kwargs.items():
            if len(k) == 1:
                if v is True:
                    args.append("-%s" % k)
                elif type(v) is not bool:
                    args.append("-%s%s" % (k, v))
            else:
                if v is True:
                    args.append("--%s" % dashify(k))
                elif type(v) is not bool:
                    args.append("--%s=%s" % (dashify(k), v))
        return args

    def _call_process(self, cmd, *args, **kwargs):
        # Handle optional arguments prior to calling transform_kwargs
        # otherwise they'll end up in args, which is bad.
        _kwargs = dict(_cwd=self._git_cwd)
        execute_kwargs = ('_cwd', '_stdin', '_decode', '_encoding', '_raw')
        for kwarg in execute_kwargs:
            if kwarg in kwargs:
                _kwargs[kwarg] = kwargs.pop(kwarg)

        # Prepare the argument list
        opt_args = self.transform_kwargs(**kwargs)
        call = ['git', dashify(cmd)] + opt_args
        call.extend(args)
        return self.execute(call, **_kwargs)


def replace_carot(cmd_arg):
    """
    Guard against the windows command shell.

    In the Windows shell, a carat character (^) may be used for
    line continuation.  To guard against this, escape the carat
    by using two of them.

    http://technet.microsoft.com/en-us/library/cc723564.aspx

    """
    return cmd_arg.replace('^', '^^')


@memoize
def instance():
    """Return the Git singleton"""
    return Git()


git = instance()
"""
Git command singleton

>>> from cola.git import git
>>> from cola.git import STDOUT
>>> 'git' == git.version()[STDOUT][:3].lower()
True

"""

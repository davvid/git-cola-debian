#!/usr/bin/env python
"""Tests various operations using the cola.git module
"""
from __future__ import absolute_import, division, unicode_literals
import unittest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from cola import git
from cola.git import STDOUT


class GitModuleTestCase(unittest.TestCase):

    @patch('cola.git.is_git_dir')
    def test_find_git_dir_None(self, is_git_dir):

        paths = git.find_git_directory(None)

        self.assertFalse(is_git_dir.called)
        self.assertEqual(None, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(None, paths.worktree)

    @patch('cola.git.is_git_dir')
    def test_find_git_dir_empty_string(self, is_git_dir):

        paths = git.find_git_directory('')

        self.assertFalse(is_git_dir.called)
        self.assertEqual(None, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(None, paths.worktree)

    @patch('cola.git.is_git_dir')
    def test_find_git_dir_never_found(self, is_git_dir):
        is_git_dir.return_value = False

        paths = git.find_git_directory('/does/not/exist')

        self.assertTrue(is_git_dir.called)
        self.assertEqual(None, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(None, paths.worktree)

        self.assertEqual(8, is_git_dir.call_count)
        kwargs = {}
        is_git_dir.assert_has_calls([
            (('/does/not/exist',), kwargs),
            (('/does/not/exist/.git',), kwargs),
            (('/does/not',), kwargs),
            (('/does/not/.git',), kwargs),
            (('/does',), kwargs),
            (('/does/.git',), kwargs),
            (('/',), kwargs),
            (('/.git',), kwargs),
        ])

    @patch('cola.git.is_git_dir')
    def test_find_git_dir_found_right_away(self, is_git_dir):
        git_dir = '/seems/to/exist/.git'
        worktree = '/seems/to/exist'
        is_git_dir.return_value = True

        paths = git.find_git_directory(git_dir)

        self.assertTrue(is_git_dir.called)
        self.assertEqual(git_dir, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(worktree, paths.worktree)

    @patch('cola.git.is_git_dir')
    def test_find_git_does_discovery(self, is_git_dir):
        git_dir = '/the/root/.git'
        worktree = '/the/root'
        is_git_dir.side_effect = lambda x: x == git_dir

        paths = git.find_git_directory('/the/root/sub/dir')

        self.assertEqual(git_dir, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(worktree, paths.worktree)

    @patch('cola.git.read_git_file')
    @patch('cola.git.is_git_file')
    @patch('cola.git.is_git_dir')
    def test_find_git_honors_git_files(self,
                                       is_git_dir,
                                       is_git_file,
                                       read_git_file):
        git_file = '/the/root/.git'
        worktree = '/the/root'
        git_dir = '/super/module/.git/modules/root'

        is_git_dir.side_effect = lambda x: x == git_file
        is_git_file.side_effect = lambda x: x == git_file
        read_git_file.return_value = git_dir

        paths = git.find_git_directory('/the/root/sub/dir')

        self.assertEqual(git_dir, paths.git_dir)
        self.assertEqual(git_file, paths.git_file)
        self.assertEqual(worktree, paths.worktree)

        kwargs = {}
        self.assertEqual(6, is_git_dir.call_count)
        is_git_dir.assert_has_calls([
            (('/the/root/sub/dir',), kwargs),
            (('/the/root/sub/dir/.git',), kwargs),
            (('/the/root/sub',), kwargs),
            (('/the/root/sub/.git',), kwargs),
            (('/the/root',), kwargs),
            (('/the/root/.git',), kwargs),
        ])
        read_git_file.assert_called_once_with('/the/root/.git')

    @patch('cola.core.getenv')
    @patch('cola.git.is_git_dir')
    def test_find_git_honors_ceiling_dirs(self, is_git_dir, getenv):

        git_dir = '/ceiling/.git'
        ceiling = '/tmp:/ceiling:/other/ceiling'
        is_git_dir.side_effect = lambda x: x == git_dir

        def mock_getenv(k, v=None):
            if k == 'GIT_CEILING_DIRECTORIES':
                return ceiling
            return v

        getenv.side_effect = mock_getenv

        paths = git.find_git_directory('/ceiling/sub/dir')

        self.assertEqual(None, paths.git_dir)
        self.assertEqual(None, paths.git_file)
        self.assertEqual(None, paths.worktree)

        self.assertEqual(4, is_git_dir.call_count)
        kwargs = {}
        is_git_dir.assert_has_calls([
            (('/ceiling/sub/dir',), kwargs),
            (('/ceiling/sub/dir/.git',), kwargs),
            (('/ceiling/sub',), kwargs),
            (('/ceiling/sub/.git',), kwargs),
        ])

    @patch('cola.core.islink')
    @patch('cola.core.isdir')
    @patch('cola.core.isfile')
    def test_is_git_dir_finds_linked_repository(self, isfile, isdir, islink):
        dirs = set([
            '/foo',
            '/foo/.git',
            '/foo/.git/refs',
            '/foo/.git/objects',
            '/foo/.git/worktrees',
            '/foo/.git/worktrees/foo',
        ])
        files = set([
            '/foo/.git/HEAD',
            '/foo/.git/worktrees/foo/HEAD',
            '/foo/.git/worktrees/foo/index',
            '/foo/.git/worktrees/foo/commondir',
            '/foo/.git/worktrees/foo/gitdir',
        ])
        islink.return_value = False
        isfile.side_effect = lambda x: x in files
        isdir.side_effect = lambda x: x in dirs

        self.assertTrue(git.is_git_dir('/foo/.git/worktrees/foo'))
        self.assertTrue(git.is_git_dir('/foo/.git'))


class GitCommandTest(unittest.TestCase):
    """Runs tests using a git.Git instance"""

    def setUp(self):
        """Creates a git.Git instance for later use"""
        self.git = git.Git()

    def test_transform_kwargs_empty(self):
        expect = []
        actual = git.transform_kwargs(foo=None, bar=False)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_single_dash_from_True(self):
        """Single dash for one-character True"""
        expect = ['-a']
        actual = git.transform_kwargs(a=True)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_no_single_dash_from_False(self):
        """No single-dash for False"""
        expect = []
        actual = git.transform_kwargs(a=False)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_double_dash_from_True(self):
        """Double-dash for longer True"""
        expect = ['--abc']
        actual = git.transform_kwargs(abc=True)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_no_double_dash_from_True(self):
        """No double-dash for False"""
        expect = []
        actual = git.transform_kwargs(abc=False)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_single_dash_int(self):
        expect = ['-a1']
        actual = git.transform_kwargs(a=1)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_double_dash_int(self):
        expect = ['--abc=1']
        actual = git.transform_kwargs(abc=1)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_single_dash_float(self):
        expect = ['-a1.5']
        actual = git.transform_kwargs(a=1.5)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_double_dash_float(self):
        expect = ['--abc=1.5']
        actual = git.transform_kwargs(abc=1.5)
        self.assertEqual(expect, actual)

    def test_transform_kwargs_single_dash_string(self):
        expect = ['-abc']
        actual = git.transform_kwargs(a='bc')
        self.assertEqual(expect, actual)

    def test_transform_double_single_dash_string(self):
        expect = ['--abc=def']
        actual = git.transform_kwargs(abc='def')
        self.assertEqual(expect, actual)

    def test_version(self):
        """Test running 'git version'"""
        version = self.git.version()[STDOUT]
        self.failUnless(version.startswith('git version'))

    def test_stdout(self):
        """Test overflowing the stdout buffer"""
        # Write to stdout only
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 0)

    def test_stderr(self):
        """Test that stderr is seen"""
        # Write to stderr and capture it
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_stdout_and_stderr(self):
        """Test ignoring stderr when stdout+stderr are provided (v2)"""
        # Write to stdout and stderr but only capture stdout
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_it_doesnt_deadlock(self):
        """Test that we don't deadlock with both stderr and stdout"""
        # 16k+1 bytes to exhaust any output buffers
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(out, '\0' * (1024 * 16 + 1))
        self.assertEqual(err, '\0' * (1024 * 16 + 1))


if __name__ == '__main__':
    unittest.main()

# Copyright (c) 2008 David Aguilar
"""Provides an inotify plugin for Linux and other systems with pyinotify"""

import os
import time

try:
    import pyinotify
    from pyinotify import ProcessEvent
    from pyinotify import WatchManager
    from pyinotify import Notifier
    from pyinotify import EventsCodes
    AVAILABLE = True
except ImportError:
    ProcessEvent = object
    AVAILABLE = False
    pass

from PyQt4 import QtCore

import cola
from cola import signals
from cola import utils

INOTIFY_EVENT = QtCore.QEvent.User + 0


_thread = None
def start():
    global _thread
    if not AVAILABLE:
        if not utils.is_linux():
            return
        msg = ('inotify: disabled\n'
               'Note: install python-pyinotify to enable inotify.\n')

        if utils.is_debian():
            msg += ('On Debian systems '
                    'try: sudo aptitude install python-pyinotify')
        cola.notifier().broadcast(signals.log_cmd, 0, msg)
        return

    # Start the notification thread
    _thread = GitNotifier()
    _thread.start()
    msg = 'inotify support: enabled'
    cola.notifier().broadcast(signals.log_cmd, 0, msg)
    cola.notifier().broadcast(signals.inotify, True)


def stop():
    if not has_inotify():
        return
    _thread.set_abort(True)
    _thread.quit()
    _thread.wait()
    

def has_inotify():
    """Return True if pyinotify is available."""
    return AVAILABLE and _thread and _thread.isRunning()


class EventReceiver(QtCore.QObject):
    def event(self, msg):
        """Overrides event() to handle custom inotify events."""
        if not AVAILABLE:
            return
        if msg.type() == INOTIFY_EVENT:
            cola.notifier().broadcast(signals.rescan)
            return True
        else:
            return False


class FileSysEvent(ProcessEvent):
    """Generated by GitNotifier in response to inotify events"""

    def __init__(self, parent):
        """Keep a reference to the QThread parent and maintain event state"""
        ProcessEvent.__init__(self)
        ## The Qt parent
        self._parent = parent
        ## Timer used to prevents notification floods
        self._last_event_time = time.time()

    def process_default(self, event):
        """Notifies the Qt parent when actions occur"""
        ## Limit the notification frequency to 1 per second
        if time.time() - self._last_event_time > 1.0:
            self._parent.notify()
        self._last_event_time = time.time()


class GitNotifier(QtCore.QThread):
    """Polls inotify for changes and generates FileSysEvents"""

    def __init__(self, timeout=250):
        """Set up the pyinotify thread"""
        QtCore.QThread.__init__(self)
        self.setTerminationEnabled(True)

        ## QApplication receiver of Qt events
        self._receiver = EventReceiver()
        ## Git command object
        self._git = cola.model().git
        ## pyinotify timeout
        self._timeout = timeout
        ## Path to monitor
        self._path = self._git.worktree()
        ## Signals thread termination
        self._abort = False
        ## Directories to watching
        self._dirs_seen = set()
        ## The inotify watch manager instantiated in run()
        self._wmgr = None
        ## Events to capture
        self._mask = (EventsCodes.ALL_FLAGS['IN_CREATE'] |
                      EventsCodes.ALL_FLAGS['IN_DELETE'] |
                      EventsCodes.ALL_FLAGS['IN_MODIFY'] |
                      EventsCodes.ALL_FLAGS['IN_MOVED_TO'])

    def set_abort(self, abort):
        """Tells the GitNotifier to abort"""
        self._abort = abort

    def notify(self):
        """Post a Qt event in response to inotify updates"""
        if not self._abort:
            event_type = QtCore.QEvent.Type(INOTIFY_EVENT)
            event = QtCore.QEvent(event_type)
            QtCore.QCoreApplication.postEvent(self._receiver, event)

    def _watch_directory(self, directory):
        """Set up a directory for monitoring by inotify"""
        if not self._wmgr:
            return
        directory = os.path.realpath(directory)
        if not os.path.exists(directory):
            return
        if directory not in self._dirs_seen:
            self._wmgr.add_watch(directory, self._mask)
            self._dirs_seen.add(directory)

    def _is_pyinotify_08x(self):
        """Is this pyinotify 0.8.x?

        The pyinotify API changed between 0.7.x and 0.8.x.
        This allows us to maintain backwards compatibility.
        """
        if hasattr(pyinotify, '__version__'):
            if pyinotify.__version__[:3] == '0.8':
                return True
        return False

    def run(self):
        """Create the inotify WatchManager and generate FileSysEvents"""
        # Only capture events that git cares about
        self._wmgr = WatchManager()
        if self._is_pyinotify_08x():
            notifier = Notifier(self._wmgr, FileSysEvent(self),
                                timeout=self._timeout)
        else:
            notifier = Notifier(self._wmgr, FileSysEvent(self))
        dirs_seen = set()
        added_flag = False
        # self._abort signals app termination.  The timeout is a tradeoff
        # between fast notification response and waiting too long to exit.
        while not self._abort:
            if not added_flag:
                self._watch_directory(self._path)
                # Register files/directories known to git
                for filename in self._git.ls_files().splitlines():
                    directory = os.path.dirname(filename)
                    self._watch_directory(directory)
                added_flag = True
            notifier.process_events()
            if self._is_pyinotify_08x():
                check = notifier.check_events()
            else:
                check = notifier.check_events(timeout=self._timeout)
            if check:
                notifier.read_events()
        notifier.stop()

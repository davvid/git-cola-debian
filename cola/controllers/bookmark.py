"""This controller handles the bookmarks dialog."""

import os
import sys

from PyQt4 import QtGui

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola import settings
from cola.views import BookmarkView

def save_bookmark():
    """
    Adds the current directory to the saved bookmarks

    In practice, the current directory is the git worktree.

    """
    model = settings.SettingsManager.settings()
    model.add_bookmark(os.getcwd())
    model.save()
    qtutils.information("Bookmark Saved")

def manage_bookmarks():
    """Launches the bookmarks manager dialog"""
    model = settings.SettingsManager.settings()
    view = BookmarkView(QtGui.QApplication.instance().activeWindow())
    ctl = BookmarkController(model, view)
    view.show()

class BookmarkController(QObserver):
    """Handles interactions with the bookmarks dialog
    """
    def __init__(self, model, view):
        """Sets up notifications and callbacks"""
        QObserver.__init__(self, model, view)
        self.add_observables('bookmarks')
        self.add_callbacks(button_open   = self.open,
                           button_delete = self.delete,
                           button_save = self.save)
        self.refresh_view()

    def save(self):
        """Saves the bookmarks settings and exits"""
        self.model.save()
        self.view.accept()

    def open(self):
        """Opens a new git-cola session on a bookmark"""
        selection = qtutils.get_selection_list(self.view.bookmarks,
                                               self.model.bookmarks)
        if not selection:
            return
        for item in selection:
            utils.fork(['git', 'cola', item])

    def delete(self):
        """Removes a bookmark from the bookmarks list"""
        selection = qtutils.get_selection_list(self.view.bookmarks,
                                               self.model.bookmarks)
        if not selection:
            return
        for item in selection:
            self.model.remove_bookmark(item)
        self.refresh_view()

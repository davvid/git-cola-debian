from __future__ import division, absolute_import, unicode_literals

import re
import subprocess

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola.i18n import N_
from cola import qtutils
from cola import utils
from cola.models import main
from cola.widgets import defs
from cola.compat import ustr


class CompletionLineEdit(QtGui.QLineEdit):

    def __init__(self, model, parent=None):
        QtGui.QLineEdit.__init__(self, parent)

        self.setFont(qtutils.diff_font())
        # used to hide the completion popup after a drag-select
        self._drag = 0

        self._keys_to_ignore = set([Qt.Key_Enter, Qt.Key_Return,
                                    Qt.Key_Escape])

        completion_model = model(self)
        completer = Completer(completion_model, self)
        completer.setWidget(self)
        self._completer = completer

        self._delegate = HighlightDelegate(self)
        self.connect(self, SIGNAL('textChanged(QString)'),
                     self._text_changed)

        completer.popup().setItemDelegate(self._delegate)
        self.connect(self._completer, SIGNAL('activated(QString)'),
                     self._complete)

    def refresh(self):
        return self._completer.model().update()

    def popup(self):
        return self._completer.popup()

    def value(self):
        return ustr(self.text())

    def _is_case_sensitive(self, text):
        return bool([char for char in text if char.isupper()])

    def _text_changed(self, text):
        text = self._last_word()
        self._do_text_changed(text)

    def _do_text_changed(self, text):
        case_sensitive = self._is_case_sensitive(text)
        if case_sensitive:
            self._completer.setCaseSensitivity(Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._delegate.set_highlight_text(text, case_sensitive)
        self._completer.set_match_text(text, case_sensitive)

    def update_matches(self):
        text = self._last_word()
        case_sensitive = self._is_case_sensitive(text)
        self._completer.model().update_matches(case_sensitive)

    def _complete(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        completion = ustr(completion)
        if not completion:
            self._do_text_changed('')
            return
        words = self._words()
        if words and not self._ends_with_whitespace():
            words.pop()

        words.append(completion)
        text = subprocess.list2cmdline(words)
        self.setText(text)
        self.emit(SIGNAL('changed()'))
        self._do_text_changed('')

    def _words(self):
        return utils.shell_split(ustr(self.text()))

    def _ends_with_whitespace(self):
        text = ustr(self.text())
        return text.rstrip() != text

    def _last_word(self):
        if self._ends_with_whitespace():
            return ''
        words = self._words()
        if not words:
            return ustr(self.text())
        if not words[-1]:
            return ''
        return words[-1]

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (event.key() == Qt.Key_Tab and
                    self.popup().isVisible()):
                event.ignore()
                return True
            if (event.key() in (Qt.Key_Return, Qt.Key_Enter) and
                    not self.popup().isVisible()):
                self.emit(SIGNAL('returnPressed()'))
                event.accept()
                return True
        if event.type() == QtCore.QEvent.Hide:
            self.close_popup()
        return QtGui.QLineEdit.event(self, event)

    def do_completion(self):
        self._completer.popup().setCurrentIndex(
                self._completer.model().index(0,0))
        self._completer.complete()

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keys_to_ignore:
                event.ignore()
                self._complete(self._last_word())
                return

        elif (event.key() == Qt.Key_Down and
              self._completer.completionCount() > 0):
            event.accept()
            self.do_completion()
            return

        QtGui.QLineEdit.keyPressEvent(self, event)

        prefix = self._last_word()
        if prefix != ustr(self._completer.completionPrefix()):
            self._update_popup_items(prefix)

        if len(event.text()) > 0 and len(prefix) > 0:
            self._completer.complete()

    #: _drag: 0 - unclicked, 1 - clicked, 2 - dragged
    def mousePressEvent(self, event):
        self._drag = 1
        return QtGui.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag == 1:
            self._drag = 2
        return QtGui.QLineEdit.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._drag != 2 and event.button() != Qt.RightButton:
            self.do_completion()
        self._drag = 0
        return QtGui.QLineEdit.mouseReleaseEvent(self, event)

    def close_popup(self):
        if self.popup().isVisible():
            self.popup().close()

    def _update_popup_items(self, prefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(prefix)
        self._completer.popup().setCurrentIndex(
                self._completer.model().index(0,0))

    def __del__(self):
        self.dispose()

    def dispose(self):
        self._completer.dispose()


class GatherCompletionsThread(QtCore.QThread):
    def __init__(self, model):
        QtCore.QThread.__init__(self)
        self.model = model
        self.case_sensitive = False

    def run(self):
        text = None
        # Loop when the matched text changes between the start and end time.
        # This happens when gather_matches() takes too long and the
        # model's matched_text changes in-between.
        while text != self.model.matched_text:
            text = self.model.matched_text
            items = self.model.gather_matches(self.case_sensitive)

        if text is not None:
            self.emit(SIGNAL('items_gathered'), items)


class HighlightDelegate(QtGui.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""
    def __init__(self, parent=None): # model, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        try:
            self.doc.setDocumentMargin(0)
        except: # older PyQt4
            pass

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold in the term name when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            return QtGui.QStyledItemDelegate.paint(self, painter, option, index)

        text = ustr(index.data().toPyObject())
        if self.case_sensitive:
            html = text.replace(self.highlight_text,
                                '<strong>%s</strong>' % self.highlight_text)
        else:
            match = re.match(r'(.*)(%s)(.*)' % re.escape(self.highlight_text),
                             text, re.IGNORECASE)
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = (start + ('<strong>%s</strong>' % middle) + end)
            else:
                html = text
        self.doc.setHtml(html)

        # Painting item without text, Text Document will paint the text
        optionV4 = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        optionV4.text = QtCore.QString()

        style = QtGui.QApplication.style()
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, optionV4, painter)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (optionV4.state & QtGui.QStyle.State_Selected):
            color = optionV4.palette.color(QtGui.QPalette.Active,
                                           QtGui.QPalette.HighlightedText)
            ctx.palette.setColor(QtGui.QPalette.Text, color)

        # translate the painter to where the text is drawn
        rect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, optionV4)
        painter.save()

        start = rect.topLeft() + QtCore.QPoint(3, 0)
        painter.translate(start)

        # tell the text document to draw the html for us
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()


class CompletionModel(QtGui.QStandardItemModel):

    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.matched_text = ''
        self.case_sensitive = False

        self.update_thread = GatherCompletionsThread(self)
        self.connect(self.update_thread, SIGNAL('items_gathered'),
                     self.apply_matches)

    def lower_completion_key(self, x):
        return x.replace('.','').lower()

    def completion_key(self, x):
        return x.replace('.','')

    def update(self):
        case_sensitive = self.update_thread.case_sensitive
        self.update_matches(case_sensitive)

    def set_match_text(self, matched_text, case_sensitive):
        self.matched_text = matched_text
        self.update_matches(case_sensitive)

    def update_matches(self, case_sensitive):
        self.case_sensitive = case_sensitive
        self.update_thread.case_sensitive = case_sensitive
        if not self.update_thread.isRunning():
            self.update_thread.start()

    def gather_matches(self, case_sensitive):
        return ((), (), set())

    def apply_matches(self, match_tuple):
        self.match_tuple = match_tuple
        matched_refs, matched_paths, dirs = match_tuple
        QStandardItem = QtGui.QStandardItem
        file_icon = qtutils.file_icon()
        dir_icon = qtutils.dir_icon()
        git_icon = qtutils.git_icon()

        matched_text = self.matched_text
        items = []
        for ref in matched_refs:
            item = QStandardItem()
            item.setText(ref)
            item.setIcon(git_icon)
            items.append(item)

        if matched_paths and (not matched_text or matched_text in '--'):
            item = QStandardItem()
            item.setText('--')
            item.setIcon(file_icon)
            items.append(item)

        for match in matched_paths:
            item = QStandardItem()
            item.setText(match)
            if match in dirs:
                item.setIcon(dir_icon)
            else:
                item.setIcon(file_icon)
            items.append(item)

        self.clear()
        self.invisibleRootItem().appendRows(items)


class Completer(QtGui.QCompleter):

    def __init__(self, model, parent):
        QtGui.QCompleter.__init__(self, parent)
        self._model = model
        self.setCompletionMode(QtGui.QCompleter.UnfilteredPopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)

        self.connect(model, SIGNAL('update()'), self.update)
        self.setModel(model)

    def update(self):
        self._model.update()

    def dispose(self):
        self._model.dispose()

    def set_match_text(self, matched_text, case_sensitive):
        self._model.set_match_text(matched_text, case_sensitive)


class GitCompletionModel(CompletionModel):

    def __init__(self, parent):
        CompletionModel.__init__(self, parent)
        self.main_model = model = main.model()
        msg = model.message_updated
        model.add_observer(msg, self.emit_update)

    def gather_matches(self, case_sensitive):
        if case_sensitive:
            transform = lambda x: x
            keyfunc = self.completion_key
        else:
            transform = lambda x: x.lower()
            keyfunc = self.lower_completion_key

        matched_text = self.matched_text
        if matched_text:
            matched_refs = [r for r in self.matches()
                            if transform(matched_text) in transform(r)]
            # if we match nothing, still offer to complete something
            if not matched_refs:
                matched_refs = self.matches()
        else:
            matched_refs = self.matches()

        matched_refs.sort(key=keyfunc)
        return (matched_refs, (), set())

    def emit_update(self):
        self.emit(SIGNAL('update()'))

    def matches(self):
        return []

    def dispose(self):
        self.main_model.remove_observer(self.emit_update)


class GitRefCompletionModel(GitCompletionModel):
    """Completer for branches and tags"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches + model.remote_branches + model.tags


class GitBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches


class GitRemoteBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.remote_branches


class GitLogCompletionModel(GitRefCompletionModel):
    """Completer for arguments suitable for git-log like commands"""

    def __init__(self, parent):
        GitRefCompletionModel.__init__(self, parent)

    def gather_matches(self, case_sensitive):
        (matched_refs, dummy_paths, dummy_dirs) =\
                GitRefCompletionModel.gather_matches(self, case_sensitive)

        file_list = self.main_model.everything()
        files = set(file_list)
        files_and_dirs = utils.add_parents(set(files))

        if case_sensitive:
            transform = lambda x: x
            keyfunc = self.completion_key
        else:
            transform = lambda x: x.lower()
            keyfunc = self.lower_completion_key

        dirs = files_and_dirs.difference(files)
        matched_text = self.matched_text
        if matched_text:
            matched_paths = [f for f in files_and_dirs
                             if transform(matched_text) in transform(f)]
        else:
            matched_paths = list(files_and_dirs)

        matched_paths.sort(key=keyfunc)

        return (matched_refs, matched_paths, dirs)


def bind_lineedit(model):
    """Create a line edit bound against a specific model"""

    class BoundLineEdit(CompletionLineEdit):

        def __init__(self, parent=None):
            CompletionLineEdit.__init__(self, model, parent)

    return BoundLineEdit

# Concrete classes
GitLogLineEdit = bind_lineedit(GitLogCompletionModel)
GitRefLineEdit = bind_lineedit(GitRefCompletionModel)
GitBranchLineEdit = bind_lineedit(GitBranchCompletionModel)
GitRemoteBranchLineEdit = bind_lineedit(GitRemoteBranchCompletionModel)


class GitDialog(QtGui.QDialog):

    def __init__(self, lineedit, title, button_text, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(333)

        self.label = QtGui.QLabel()
        self.label.setText(title)

        self.lineedit = lineedit(self)
        self.setFocusProxy(self.lineedit)

        self.ok_button = QtGui.QPushButton()
        self.ok_button.setText(button_text)
        self.ok_button.setIcon(qtutils.apply_icon())

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setMargin(defs.no_margin)
        self.button_layout.setSpacing(defs.button_spacing)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.lineedit)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.ok_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.connect(self.lineedit, SIGNAL('textChanged(const QString&)'),
                     self.text_changed)

        self.setWindowModality(Qt.WindowModal)
        self.ok_button.setEnabled(False)

    def text(self):
        return ustr(self.lineedit.text())

    def text_changed(self, txt):
        self.ok_button.setEnabled(bool(self.text()))

    def set_text(self, ref):
        self.lineedit.setText(ref)

    @classmethod
    def get(cls, title, button_text, parent, default=None):
        dlg = cls(title, button_text, parent)
        if default:
            dlg.set_text(default)

        dlg.show()
        dlg.raise_()

        def show_popup():
            x = dlg.lineedit.x()
            y = dlg.lineedit.y() + dlg.lineedit.height()
            point = QtCore.QPoint(x, y)
            mapped = dlg.mapToGlobal(point)
            dlg.lineedit.popup().move(mapped.x(), mapped.y())
            dlg.lineedit.popup().show()
            dlg.lineedit.refresh()

        QtCore.QTimer().singleShot(0, show_popup)

        if dlg.exec_() == cls.Accepted:
            return dlg.text()
        else:
            return None


class GitRefDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitRefLineEdit,
                           title, button_text, parent)


class GitBranchDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitBranchLineEdit,
                           title, button_text, parent)


class GitRemoteBranchDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitRemoteBranchLineEdit,
                           title, button_text, parent)

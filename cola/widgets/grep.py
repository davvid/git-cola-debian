from __future__ import division, absolute_import, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import hotkeys
from .. import utils
from .. import qtutils
from ..cmds import do
from ..git import git
from ..i18n import N_
from ..qtutils import diff_font
from ..utils import Group
from .standard import Dialog
from .text import VimHintedTextView, HintedLineEdit
from . import defs


def grep():
    """Prompt and use 'git grep' to find the content."""
    widget = new_grep(parent=qtutils.active_window())
    widget.show()
    widget.raise_()
    return widget


def new_grep(text=None, parent=None):
    widget = Grep(parent=parent)
    if text:
        widget.search_for(text)
    return widget


def goto_grep(line):
    """Called when Search -> Grep's right-click 'goto' action."""
    filename, line_number, contents = line.split(':', 2)
    do(cmds.Edit, [filename], line_number=line_number)


class GrepThread(QtCore.QThread):
    result = Signal(object, object, object)

    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.query = None
        self.shell = False
        self.regexp_mode = '--basic-regexp'

    def run(self):
        if self.query is None:
            return
        query = self.query
        if self.shell:
            args = utils.shell_split(query)
        else:
            args = [query]
        status, out, err = git.grep(self.regexp_mode, n=True, *args)
        if query == self.query:
            self.result.emit(status, out, err)
        else:
            self.run()


class Grep(Dialog):

    def __init__(self, parent=None):
        Dialog.__init__(self, parent)
        self.setWindowTitle(N_('Search'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.edit_action = qtutils.add_action(
                self, N_('Edit'), self.edit, hotkeys.EDIT)

        self.refresh_action = qtutils.add_action(
                self, N_('Refresh'), self.search, *hotkeys.REFRESH_HOTKEYS)

        self.input_label = QtWidgets.QLabel('git grep')
        self.input_label.setFont(diff_font())

        self.input_txt = HintedLineEdit(N_('command-line arguments'), self)
        self.input_txt.hint.enable(True)

        self.regexp_combo = combo = QtWidgets.QComboBox()
        combo.setToolTip(N_('Choose the "git grep" regular expression mode'))
        items = [N_('Basic Regexp'), N_('Extended Regexp'), N_('Fixed String')]
        combo.addItems(items)
        combo.setCurrentIndex(0)
        combo.setEditable(False)
        combo.setItemData(
                0,
                N_('Search using a POSIX basic regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(
                1,
                N_('Search using a POSIX extended regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(2, N_('Search for a fixed string'), Qt.ToolTipRole)
        combo.setItemData(0, '--basic-regexp', Qt.UserRole)
        combo.setItemData(1, '--extended-regexp', Qt.UserRole)
        combo.setItemData(2, '--fixed-strings', Qt.UserRole)

        self.result_txt = GrepTextView(N_('grep result...'), self)
        self.result_txt.hint.enable(True)

        self.edit_button = qtutils.edit_button()
        qtutils.button_action(self.edit_button, self.edit_action)

        self.refresh_button = qtutils.refresh_button()
        qtutils.button_action(self.refresh_button, self.refresh_action)

        text = N_('Shell arguments')
        tooltip = N_('Parse arguments using a shell.\n'
                     'Queries with spaces will require "double quotes".')
        self.shell_checkbox = qtutils.checkbox(text=text, tooltip=tooltip,
                                               checked=False)
        self.close_button = qtutils.close_button()

        self.refresh_group = Group(self.refresh_action, self.refresh_button)
        self.refresh_group.setEnabled(False)

        self.edit_group = Group(self.edit_action, self.edit_button)
        self.edit_group.setEnabled(False)

        self.input_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                         self.input_label, self.input_txt,
                                         self.regexp_combo)

        self.bottom_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          self.edit_button, self.refresh_button,
                                          self.shell_checkbox, qtutils.STRETCH,
                                          self.close_button)

        self.mainlayout = qtutils.vbox(defs.margin, defs.no_spacing,
                                       self.input_layout, self.result_txt,
                                       self.bottom_layout)
        self.setLayout(self.mainlayout)

        thread = self.worker_thread = GrepThread(self)
        thread.result.connect(self.process_result, type=Qt.QueuedConnection)

        self.input_txt.textChanged.connect(lambda s: self.search())
        self.regexp_combo.currentIndexChanged.connect(lambda x: self.search())
        self.result_txt.leave.connect(self.input_txt.setFocus)

        qtutils.add_action(self.input_txt, 'Focus Results', self.focus_results,
                           hotkeys.DOWN, *hotkeys.ACCEPT)
        qtutils.add_action(self, 'Focus Input', self.focus_input, hotkeys.FOCUS)

        qtutils.connect_toggle(self.shell_checkbox, lambda x: self.search())
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        self.init_state(None, self.resize_widget, parent)

    def resize_widget(self, parent):
        width, height = qtutils.default_size(parent, 666, 420)
        self.resize(width, height)

    def focus_input(self):
        self.input_txt.setFocus()
        self.input_txt.selectAll()

    def focus_results(self):
        self.result_txt.setFocus()

    def done(self, exit_code):
        self.save_state()
        return Dialog.done(self, exit_code)

    def regexp_mode(self):
        idx = self.regexp_combo.currentIndex()
        return self.regexp_combo.itemData(idx, Qt.UserRole)

    def search(self):
        self.edit_group.setEnabled(False)
        self.refresh_group.setEnabled(False)
        query = self.input_txt.value()
        if len(query) < 2:
            self.result_txt.set_value('')
            return
        self.worker_thread.query = query
        self.worker_thread.shell = self.shell_checkbox.isChecked()
        self.worker_thread.regexp_mode = self.regexp_mode()
        self.worker_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)

    def text_scroll(self):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar:
            return scrollbar.value()
        return None

    def set_text_scroll(self, scroll):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar and scroll is not None:
            scrollbar.setValue(scroll)

    def text_offset(self):
        return self.result_txt.textCursor().position()

    def set_text_offset(self, offset):
        cursor = self.result_txt.textCursor()
        cursor.setPosition(offset)
        self.result_txt.setTextCursor(cursor)

    def process_result(self, status, out, err):

        if status == 0:
            value = out + err
        elif out + err:
            value = 'git grep: ' + out + err
        else:
            value = ''

        # save scrollbar and text cursor
        scroll = self.text_scroll()
        offset = min(len(value), self.text_offset())

        self.result_txt.set_value(value)
        # restore
        self.set_text_scroll(scroll)
        self.set_text_offset(offset)

        enabled = status == 0
        self.edit_group.setEnabled(enabled)
        self.refresh_group.setEnabled(True)

    def edit(self):
        goto_grep(self.result_txt.selected_line()),


class GrepTextView(VimHintedTextView):

    def __init__(self, hint, parent):
        VimHintedTextView.__init__(self, hint=hint, parent=parent)

        self.goto_action = qtutils.add_action(self, 'Launch Editor', self.edit)
        self.goto_action.setShortcut(hotkeys.EDIT)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def edit(self):
        goto_grep(self.selected_line())

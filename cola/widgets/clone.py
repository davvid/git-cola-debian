from __future__ import division, absolute_import, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import core
from .. import icons
from .. import utils
from .. import qtutils
from ..i18n import N_
from ..interaction import Interaction
from . import defs
from . import standard
from . import text
from ..models import main


def prompt_for_clone(show=True, settings=None):
    """Presents a GUI for cloning a repository"""
    view = Clone(settings=settings, parent=qtutils.active_window())
    if show:
        view.show()
        view.raise_()
    return view


class Clone(standard.Dialog):

    # Signal binding for returning the input data
    result = QtCore.Signal(object, object, bool, bool)

    def __init__(self, settings=None, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(N_('Clone Repository'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # Repository location
        self.url_label = QtWidgets.QLabel(N_('URL'))
        hint = 'git://git.example.com/repo.git'
        self.url = text.HintedLineEdit(hint, parent=self)
        self.url.setToolTip(N_('Path or URL to clone (Env. $VARS okay)'))

        # Initialize submodules
        self.submodules = qtutils.checkbox(
            text=N_('Inititalize submodules'), checked=False)

        # Reduce commit history
        self.shallow = qtutils.checkbox(
            text=N_('Reduce commit history to minimum'), checked=False)

        # Buttons
        self.ok_button = qtutils.create_button(
            text=N_('Clone'), icon=icons.ok(), default=True)
        self.close_button = qtutils.close_button()

        # Form layout for inputs
        self.input_layout = qtutils.form(
            defs.no_margin, defs.button_spacing,
            (self.url_label, self.url))

        self.button_layout = qtutils.hbox(
            defs.margin, defs.spacing,
            self.submodules, defs.button_spacing,
            self.shallow, qtutils.STRETCH,
            self.ok_button, self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.input_layout, self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.close)
        qtutils.connect_button(self.ok_button, self.prepare_to_clone)
        self.url.textChanged.connect(lambda x: self.update_actions())

        self.init_state(settings, self.resize, 720, 200)
        self.update_actions()

    def update_actions(self):
        url = self.url.value().strip()
        enabled = bool(url)
        self.ok_button.setEnabled(enabled)

    def prepare_to_clone(self):
        """Grabs and validates the input data"""

        submodules = self.submodules.isChecked()
        shallow = self.shallow.isChecked()

        url = self.url.value()
        url = utils.expandpath(url)
        if not url:
            return None
        try:
            # Pick a suitable basename by parsing the URL
            newurl = url.replace('\\', '/').rstrip('/')
            default = newurl.rsplit('/', 1)[-1]
            if default == '.git':
                # The end of the URL is /.git, so assume it's a file path
                default = os.path.basename(os.path.dirname(newurl))
            if default.endswith('.git'):
                # The URL points to a bare repo
                default = default[:-4]
            if url == '.':
                # The URL is the current repo
                default = os.path.basename(core.getcwd())
            if not default:
                raise
        except:
            Interaction.information(
                    N_('Error Cloning'),
                    N_('Could not parse Git URL: "%s"') % url)
            Interaction.log(N_('Could not parse Git URL: "%s"') % url)
            return None

        # Prompt the user for a directory to use as the parent directory
        msg = N_('Select a parent directory for the new clone')
        dirname = qtutils.opendir_dialog(msg, main.model().getcwd())
        if not dirname:
            return None
        count = 1
        destdir = os.path.join(dirname, default)
        olddestdir = destdir
        if core.exists(destdir):
            # An existing path can be specified
            msg = (
                N_('"%s" already exists, cola will create a new directory')
                % destdir)
            Interaction.information(N_('Directory Exists'), msg)

        # Make sure the new destdir doesn't exist
        while core.exists(destdir):
            destdir = olddestdir + str(count)
            count += 1

        # Return the input data and close the dialog
        self.result.emit(url, destdir, submodules, shallow)
        self.close()

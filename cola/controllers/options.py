"""This module provides the controller for the options gui

"""

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import qtutils
from cola import serializer
from cola.views import option
from cola.qobserver import QObserver


def update_options():
    """Launch the options window given a model and parent widget."""
    parent = QtGui.QApplication.instance().activeWindow()
    view = option.OptionsView(parent)
    ctl = OptionsController(view)
    view.show()
    return view.exec_() == QtGui.QDialog.Accepted


class OptionsController(QObserver):
    """Provides control to the options dialog."""

    def __init__(self, view):
        ## operate on a clone of the original model
        QObserver.__init__(self, serializer.clone(cola.model()), view)

        ## used to restore original values when cancelling
        self._backup_model = serializer.clone(cola.model())

        ## config params modified by the gui
        self.add_observables('local_user_email',
                             'local_user_name',
                             'local_merge_summary',
                             'local_merge_diffstat',
                             'local_merge_verbosity',
                             'local_gui_diffcontext',
                             'global_user_email',
                             'global_user_name',
                             'global_merge_keepbackup',
                             'global_merge_summary',
                             'global_merge_diffstat',
                             'global_merge_verbosity',
                             'global_gui_editor',
                             'global_merge_tool',
                             'global_diff_tool',
                             'global_gui_diffcontext',
                             'global_gui_historybrowser',
                             'global_cola_fontdiff_size',
                             'global_cola_fontdiff',
                             'global_cola_savewindowsettings',
                             'global_cola_tabwidth')

        # Refresh before registering callbacks to avoid extra notifications
        self.refresh_view()

        # Register actions
        self.add_actions(global_cola_fontdiff = self.tell_parent_model)
        self.add_callbacks(global_cola_fontdiff_size = self.update_size)
        self.add_actions(global_cola_tabwidth = self.tell_parent_model)
        self.add_callbacks(save_button = self.save_settings)
        self.connect(self.view, SIGNAL('rejected()'), self.restore_settings)

    def refresh_view(self):
        """Apply the configured font and update widgets."""
        # The fixed-width console font
        qtutils.set_diff_font(self.view.global_cola_fontdiff)
        # Label the group box around the local repository
        self.view.local_groupbox.setTitle(unicode(self.tr('%s Repository'))
                                          % self.model.project)
        QObserver.refresh_view(self)

    def save_settings(self):
        """Save updated config variables back to git."""
        params_to_save = []
        params = self.model.config_params()
        for param in params:
            value = self.model.param(param)
            backup = self._backup_model.param(param)
            if value != backup:
                params_to_save.append(param)
        for param in params_to_save:
            self.model.save_config_param(param)
        # Update the main model with any changed parameters
        cola.model().copy_params(self.model, params_to_save)
        self.view.done(QtGui.QDialog.Accepted)

    def restore_settings(self):
        """Reverts any changes done in the Options dialog."""
        params = (self._backup_model.config_params() +
                  ['global_cola_fontdiff_size'])
        self.model.copy_params(self._backup_model, params)
        self.tell_parent_model()

    def tell_parent_model(self,*rest):
        """Notifies the main app's model about changed parameters"""
        params= ('global_cola_fontdiff',
                 'global_cola_fontdiff_size',
                 'global_cola_savewindowsettings',
                 'global_cola_tabwidth')
        for param in params:
            cola.model().set_param(param, self.model.param(param))

    def update_size(self, *rest):
        """Updates fonts whenever font sizes change"""
        # The fixed-width console font combobox
        font = str(self.view.global_cola_fontdiff.currentFont().toString())
        default = self.model.global_cola_fontdiff or font
        self.model.apply_diff_font_size(default)
        self.tell_parent_model()

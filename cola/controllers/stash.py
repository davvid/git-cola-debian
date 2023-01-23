"""This controller handles the stash dialog."""


import os

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import StashView

def stash(model, parent):
    """Launches a stash dialog using the provided model + view
    """
    model = model.clone()
    model.keep_index = True
    model.stash_list = []
    model.stash_revids = []
    view = StashView(parent)
    ctl = StashController(model, view)
    view.show()

class StashController(QObserver):
    """The StashController is the brains behind the 'Stash' dialog
    """
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_observables('stash_list', 'keep_index')
        self.add_callbacks(button_stash_show  = self.stash_show,
                           button_stash_apply = self.stash_apply,
                           button_stash_drop  = self.stash_drop,
                           button_stash_clear = self.stash_clear,
                           button_stash_save  = self.stash_save)
        self.update_model()

    def update_model(self):
        """Initiates git queries on the model and updates the view
        """
        self.model.set_stash_list(self.model.parse_stash_list())
        self.model.set_stash_revids(self.model.parse_stash_list(revids=True))
        self.refresh_view()

    def get_selected_stash(self):
        """Returns the stash name of the currently selected stash
        """
        list_widget = self.view.stash_list
        stash_list = self.model.get_stash_revids()
        return qtutils.get_selected_item(list_widget, stash_list)

    def stash_save(self):
        """Saves the worktree in a stash

        This prompts the user for a stash name and creates
        a git stash named accordingly.
        """
        if not qtutils.question(self.view,
                                self.tr('Stash Changes?'),
                                self.tr('This will stash your current '
                                        'changes away for later use.\n'
                                        'Continue?')):
            return

        stash_name, ok = qtutils.input(self.tr('Enter a name for this stash'))
        if not ok:
            return
        while stash_name in self.model.get_stash_list():
            qtutils.information(self.tr("Oops!"),
                                self.tr('That name already exists.  '
                                        'Please enter another name.'))
            stash_name, ok = qtutils.input(self.tr('Enter a name for '
                                                   'this stash'))
            if not ok:
                return

        if not stash_name:
            return

        # Sanitize our input, just in case
        stash_name = utils.sanitize_input(stash_name)
        args = []
        if self.model.get_keep_index():
            args.append('--keep-index')
        args.append(stash_name)

        qtutils.log(self.model.git.stash('save', *args),
                    quiet=False,
                    doraise=True)
        self.view.accept()

    def stash_show(self):
        """Shows the current stash in the main view."""
        selection = self.get_selected_stash()
        if not selection:
            return
        diffstat = self.model.git.stash('show', selection)
        diff = self.model.git.stash('show', '-p', selection)
        self.view.parent_view.display('%s\n\n%s' % (diffstat, diff))

    def stash_apply(self):
        """Applies the currently selected stash
        """
        selection = self.get_selected_stash()
        if not selection:
            return
        out = self.model.git.stash('apply', '--index', selection,
                                   with_stderr=True)
        qtutils.log(out, quiet=False, doraise=True)
        self.view.accept()

    def stash_drop(self):
        """Drops the currently selected stash
        """
        selection = self.get_selected_stash()
        if not selection:
            return
        if not qtutils.question(self.view,
                                self.tr('Drop Stash?'),
                                self.tr('This will permanently remove the '
                                        'selected stash.\n'
                                        'Recovering these changes may not '
                                        'be possible.\n\n'
                                        'Continue?')):
            return
        qtutils.log(self.model.git.stash('drop', selection),
                    quiet=False,
                    doraise=True)
        self.update_model()

    def stash_clear(self):
        """Clears all stashes
        """
        if not qtutils.question(self.view,
                                self.tr('Drop All Stashes?'),
                                self.tr('This will permanently remove '
                                        'ALL stashed changes.\n'
                                        'Recovering these changes may not '
                                        'be possible.\n\n'
                                        'Continue?')):
            return
        self.model.git.stash('clear'),
        self.update_model()

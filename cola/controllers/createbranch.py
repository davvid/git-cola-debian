#!/usr/bin/env python
"""This controller handles the create branch dialog."""


import os
from PyQt4.QtGui import QDialog

from cola import utils
from cola import qtutils
from cola.views import CreateBranchView
from cola.qobserver import QObserver

def create_new_branch(model,parent,revision=''):
    model = model.clone()
    view = CreateBranchView(parent)
    ctl = CreateBranchController(model, view)
    model.set_revision(revision)
    view.show()
    return view.exec_() == QDialog.Accepted

class CreateBranchController(QObserver):
    def init(self, model, view):
        self._remoteclicked = False
        self.add_observables('revision', 'local_branch')
        self.add_callbacks(branch_list   = self.item_changed,
                           create_button = self.create_branch,
                           local_radio   = self.display_model,
                           remote_radio  = self.display_model,
                           tag_radio     = self.display_model)
        self.display_model()

    #+--------------------------------------------------------------------
    #+ Qt callbacks
    def create_branch(self):
        """This callback is called when the "Create Branch"
        button is called."""

        revision = self.model.get_revision()
        branch = self.model.get_local_branch()
        existing_branches = self.model.get_local_branches()

        if not branch or not revision:
            qtutils.information(
                self.tr('Missing Data'),
                self.tr('Please provide both a branch'
                       +' name and revision expression.'))
            return

        check_branch = False
        if branch in existing_branches:
            if self.view.no_update_radio.isChecked():
                msg = self.tr("Branch '%s' already exists.")
                msg = unicode(msg) % branch
                qtutils.information( self.tr('warning'), msg )
                return
            # Whether we should prompt the user for lost commits
            commits = self.model.rev_list_range(revision, branch)
            check_branch = bool(commits)

        if check_branch:
            msg = self.tr("Resetting '%s' to '%s' will "
                          "lose the following commits:")
            lines = [ unicode(msg) % (branch, revision) ]

            for idx, commit in enumerate(commits):
                subject = commit[1][0:min(len(commit[1]),16)]
                if len(subject) < len(commit[1]):
                    subject += '...'
                lines.append('\t' + commit[0][:8]
                        +'\t' + subject)
                if idx >= 5:
                    skip = len(commits) - 5
                    lines.append('\t(%d skipped)' % skip)
                    break

            lines.extend([
                unicode(self.tr('Recovering lost commits may not be easy.')),
                unicode(self.tr("Reset '%s'?")) % branch
                ])

            result = qtutils.question(self.view, self.tr('warning'),
                                      '\n'.join(lines))
            if not result:
                return

        track = self.view.remote_radio.isChecked()
        fetch = self.view.fetch_checkbox.isChecked()
        ffwd = self.view.ffwd_only_radio.isChecked()
        reset = self.view.reset_radio.isChecked()
        chkout = self.view.checkout_checkbox.isChecked()

        output = self.model.create_branch(branch, revision, track=track)
        qtutils.show_output(output)
        if chkout:
            status, out, err = self.model.git.checkout(branch,
                                                       with_extended_output=True)
            qtutils.show_output(out+err)

        self.view.accept()

    def item_changed(self, *rest):
        """This callback is called when the item selection changes
        in the branch_list."""

        qlist = self.view.branch_list
        ( row, selected ) = qtutils.get_selected_row(qlist)
        if not selected: return

        sources = self.__get_branch_sources()
        rev = sources[row]

        # Update the model with the selection
        self.model.set_revision(rev)

        # Only set the branch name field if we're
        # branching from a remote branch.
        if not self.view.remote_radio.isChecked():
            return
        branch = utils.basename(rev)
        if branch == 'HEAD':
            return
        # Signal that we've clicked on a remote branch
        self._remoteclicked = True
        self.model.set_local_branch(branch)
        self._remoteclicked = False

    ######################################################################

    def display_model(self):
        branches = self.__get_branch_sources()
        qtutils.set_items(self.view.branch_list, branches)

    def __get_branch_sources(self):
        """Get the list of items for populating the branch root list."""
        if self.view.local_radio.isChecked():
            return self.model.get_local_branches()
        elif self.view.remote_radio.isChecked():
            return self.model.get_remote_branches()
        elif self.view.tag_radio.isChecked():
            return self.model.get_tags()

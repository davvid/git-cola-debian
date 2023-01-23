"""Translate signals from the merge dialog."""
from cola.ctrl import Controller
from cola.merge.model import command_directory

class MergeController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)
        self.add_commands(command_directory)

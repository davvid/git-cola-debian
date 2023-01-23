""" Provides the GitCommandWidget dialog. """
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import qtutils
from cola.views import standard


def run_command(parent, title, command, params):
    """Show a command widget """

    view = GitCommandWidget(parent)
    view.setWindowModality(QtCore.Qt.ApplicationModal)
    view.set_command(command, params)
    view.setWindowTitle(title)
    if not parent:
        qtutils.center_on_screen(view)
    view.run()
    view.show()
    status = view.exec_()
    return (view.exitstatus, view.out, view.err)


class GitCommandWidget(standard.StandardDialog):
    ''' Nice TextView that reads the output of a command syncronously '''
    # Keep us in scope otherwise PyQt kills the widget
    _instances = set()

    def __del__(self):
        self._instances.remove(self)

    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)
        self._instances.add(self)
        self.resize(720, 420)

        # Construct the process
        self.proc = QtCore.QProcess(self)
        self.exitstatus = 0
        self.out = ''
        self.err = ''

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)

        # Create the text browser
        self.output_text = QtGui.QTextBrowser(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)

        self._layout.addWidget(self.output_text)

        # Create abort / close buttons
        self.button_abort = QtGui.QPushButton(self)
        self.button_abort.setText(self.tr('Abort'))
        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(self.tr('Close'))

        # Put them in a horizontal layout at the bottom.
        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.addButton(self.button_abort, QtGui.QDialogButtonBox.RejectRole)
        self.button_box.addButton(self.button_close, QtGui.QDialogButtonBox.AcceptRole)
        self._layout.addWidget(self.button_box)

        # Connect the signals to the process
        self.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self.readOutput)
        self.connect(self.proc, SIGNAL("readyReadStandardError()"), self.readErrors)
        self.connect(self.proc, SIGNAL('finished(int)'), self.finishProc)
        self.connect(self.proc, SIGNAL('stateChanged(QProcess::ProcessState)'), self.stateChanged)

        # Connect the signlas to the buttons
        self.connect(self.button_abort, SIGNAL('clicked()'), self.abortProc)
        self.connect(self.button_close, SIGNAL('clicked()'), self.close)
        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort.setEnabled(False)

    def set_command(self, command, params):
        '''command : the shell command to spawn
           params  : parameters of the command '''
        self.command = command
        self.params = params

    def run(self):
        ''' Runs the process '''
        self.proc.start(self.command, QtCore.QStringList(self.params))

    def readOutput(self):
        rawbytes = self.proc.readAllStandardOutput()
        data = ''
        for b in rawbytes:
            data += b
        self.out += data
        self.append_text(data)

    def readErrors(self):
        rawbytes = self.proc.readAllStandardError()
        data = ''
        for b in rawbytes:
            data += b
        self.err += data
        self.append_text(data)

    def append_text(self, txt):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(core.decode(txt))
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def abortProc(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # Terminate seems to do nothing in windows
            self.proc.terminate()
            # Kill the process.
            QtCore.QTimer.singleShot(1000, self.proc, QtCore.SLOT("kill()"))

    def closeEvent(self, event):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # The process is still running, make sure we really want to abort.
            reply = QtGui.QMessageBox.question(self, 'Message',
                    self.tr("Abort process?"), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.abortProc()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def stateChanged(self, newstate):
        # State of process has changed - change the abort button state.
        if newstate == QtCore.QProcess.NotRunning:
            self.button_abort.setEnabled(False)
        else:
            self.button_abort.setEnabled(True)

    def finishProc(self, status ):
        self.exitstatus = status

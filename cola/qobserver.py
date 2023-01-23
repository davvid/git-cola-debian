# Copyright (c) 2008 David Aguilar
"""This module provides the QObserver class which allows for simple
correspondancies between model parameters and Qt widgets.

The QObserver class handles receiving notifications from
model classes and updating Qt widgets accordingly.

Qt signals are also relayed back to the model so that changes
are always available in the model without having to worry about the
different ways to query Qt widgets.

"""
from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import observer

class QObserver(observer.Observer, QtCore.QObject):

    def __init__(self, model, view, *args, **kwargs):
        """Binds a model and Qt view"""
        observer.Observer.__init__(self, model)
        QtCore.QObject.__init__(self)

        self.view = view

        self._actions = {}
        self._callbacks = {}
        self._model_to_view = {}
        self._view_to_model = {}
        self._connected = set()
        self._in_textfield = False
        self._in_callback = False

    def SLOT(self, *args):
        """Default slot to handle all Qt callbacks.
        This method delegates to callbacks from add_signals."""

        self._in_textfield = False

        widget = self.sender()
        sender = str(widget.objectName())

        if sender in self._view_to_model:
            model = self.model
            model_param = self._view_to_model[sender]
            if isinstance(widget, QtGui.QTextEdit):
                self._in_textfield = True
                value = unicode(widget.toPlainText())
                model.set_param(model_param, value,
                                notify=False)
            elif isinstance(widget, QtGui.QLineEdit):
                self._in_textfield = True
                value = unicode(widget.text())
                model.set_param(model_param, value)
            elif isinstance(widget, QtGui.QCheckBox):
                model.set_param(model_param, widget.isChecked())
            elif isinstance(widget, QtGui.QSpinBox):
                model.set_param(model_param, widget.value())
            elif isinstance(widget, QtGui.QFontComboBox):
                value = unicode(widget.currentFont().toString())
                if model.has_param(model_param+'_size'):
                    size = model.get_param(model_param+'_size')
                    props = value.split(',')
                    props[1] = str(size)
                    value = ','.join(props)
                model.set_param(model_param, value)
            elif isinstance(widget, QtGui.QDateEdit):
                fmt = QtCore.Qt.ISODate
                value = str(widget.date().toString(fmt))
                model.set_param(model_param, value)
            elif isinstance(widget, QtGui.QListWidget):
                row = widget.currentRow()
                item = widget.item(row)
                if item:
                    selected = item.isSelected()
                else:
                    selected = False
                model.set_param(model_param+'_selected', selected)
                model.set_param(model_param+'_index', row)
                if selected and row != -1:
                    model.set_param(model_param+'_item',
                                    model.get_param(model_param)[row])
                else:
                    model.set_param(model_param+'_item', '')
            elif isinstance(widget, QtGui.QTreeWidget):
                item = widget.currentItem()
                if item:
                    selected = item.isSelected()
                    row = widget.indexOfTopLevelItem(item)
                else:
                    selected = False
                    row = -1
                model.set_param(model_param+'_selected', selected)
                model.set_param(model_param+'_index', row)
                items = model.get_param(model_param)
                if selected and row != -1 and row < len(items):
                    model.set_param(model_param+'_item', items[row])
                else:
                    model.set_param(model_param+'_item', '')
            elif isinstance(widget, QtGui.QComboBox):
                idx = widget.currentIndex()
                model.set_param(model_param+'_index', idx)
                if idx != -1 and model.get_param(model_param):
                    model.set_param(model_param+'_item',
                                   model.get_param(model_param)[idx])
                else:
                    model.set_param(model_param+'_item', '')

            else:
                print("SLOT(): Unknown widget:", sender, widget)

        self._in_callback = True
        if sender in self._callbacks:
            self._callbacks[sender](*args)
        self._in_callback = False
        self._in_textfield = False

    def connect(self, obj, signal_str, *args):
        """Convenience function so that subclasses do not have
        to import QtCore.SIGNAL."""
        signal = signal_str
        if type(signal) is str:
            signal = QtCore.SIGNAL(signal)
        return QtCore.QObject.connect(obj, signal, *args)

    def add_signals(self, signal_str, *objects):
        """Connects object's signal to the QObserver."""
        for obj in objects:
            self.connect(obj, signal_str, self.SLOT)

    def add_callbacks(self, **callbacks):
        """Registers callbacks that are called in response to GUI events."""
        for sender, callback in callbacks.iteritems():
            self._callbacks[sender] = callback
            self.autoconnect(getattr(self.view, sender))

    def add_observables(self, *params):
        """This method assumes that widgets and model params
        share the same name."""
        for param in params:
            self.model_to_view(param, getattr(self.view, param))

    def model_to_view(self, model_param, *widgets):
        """Binds model params to qt widgets(model->view)"""
        self._model_to_view[model_param] = widgets
        for w in widgets:
            view = str(w.objectName())
            self._view_to_model[view] = model_param
            self._autoconnect(w)

    def autoconnect(self, *widgets):
        for w in widgets:
            self._autoconnect(w)

    def _autoconnect(self, widget):
        """Automagically connects Qt widgets to QObserver.SLOT"""

        if widget in self._connected:
            return
        self._connected.add(widget)

        if isinstance(widget, QtGui.QTextEdit):
            self.add_signals('textChanged()', widget)
        elif isinstance(widget, QtGui.QLineEdit):
            self.add_signals('textChanged(const QString&)', widget)
        elif isinstance(widget, QtGui.QListWidget):
            self.add_signals('itemSelectionChanged()', widget)
            self.add_signals('itemClicked(QListWidgetItem *)', widget)
            doubleclick = str(widget.objectName())+'_doubleclick'
            if hasattr(self, doubleclick):
                self.connect(widget, 'itemDoubleClicked(QListWidgetItem *)',
                             getattr(self, doubleclick))
        elif isinstance(widget, QtGui.QTreeWidget):
            self.add_signals('itemSelectionChanged()', widget)
            self.add_signals('itemClicked(QTreeWidgetItem *, int)', widget)
            doubleclick = str(widget.objectName())+'_doubleclick'
            if hasattr(self, doubleclick):
                self.connect(widget, 'itemDoubleClicked(QTreeWidgetItem *, int)',
                             getattr(self, doubleclick))

        elif isinstance(widget, QtGui.QAbstractButton):
            self.add_signals('released()', widget)
        elif isinstance(widget, QtGui.QAction):
            self.add_signals('triggered()', widget)
        elif isinstance(widget, QtGui.QCheckBox):
            self.add_signals('stateChanged(int)', widget)
        elif isinstance(widget, QtGui.QSpinBox):
            self.add_signals('valueChanged(int)', widget)
        elif isinstance(widget, QtGui.QFontComboBox):
            self.add_signals('currentFontChanged(const QFont&)', widget)
        elif isinstance(widget, QtGui.QSplitter):
            self.add_signals('splitterMoved(int,int)', widget)
        elif isinstance(widget, QtGui.QDateEdit):
            self.add_signals('dateChanged(const QDate&)', widget)
        elif isinstance(widget, QtGui.QComboBox):
            self.add_signals('currentIndexChanged(int)', widget)
        else:
            raise Exception('Asked to connect unknown widget:\n\t%s => %s'
                            % (type(widget), str(widget.objectName())))

    def add_actions(self, **kwargs):
        """Register view actions that are called in response to
        view changes.(view->model)"""
        for model_param, callback in kwargs.iteritems():
            if type(callback) is list:
                self._actions[model_param] = callback
            else:
                self._actions[model_param] = [callback]

    def subject_changed(self, param, value):
        """Sends a model param to the view(model->view)"""

        if self._in_textfield and not self._in_callback:
            # A slot has changed the model and we're not in
            # a user callback.  In this case the event is causing
            # a feedback loop so skip redundant work and return.
            return

        if param in self._model_to_view:
            notify = self.model.get_notify()
            self.model.set_notify(False)
            for widget in self._model_to_view[param]:
                sender = str(widget.objectName())
                if isinstance(widget, QtGui.QSpinBox):
                    widget.setValue(value)
                elif isinstance(widget, QtGui.QPixmap):
                    widget.load(value)
                elif isinstance(widget, QtGui.QTextEdit):
                    widget.setText(value)
                elif isinstance(widget, QtGui.QLineEdit):
                    widget.setText(value)
                elif isinstance(widget, QtGui.QListWidget):
                    self.model.set_param(param+'_item', '')
                    widget.clear()
                    for i in value:
                        widget.addItem(i)
                    if self.model.has_param(param+'_index'):
                        idx = self.model.get_param(param+'_index')
                        if idx != -1 and idx < len(value):
                            item = widget.item(idx)
                            widget.setCurrentItem(item)
                            widget.setItemSelected(item, True)
                            self.model.set_param(param+'_item', value[idx])
                            if sender in self._callbacks:
                                self.model.set_notify(True)
                                self._callbacks[sender]()
                                self.model.set_notify(False)
                        else:
                            self.model.set_param(param+'_item', '')
                elif isinstance(widget, QtGui.QTreeWidget):
                    self.model.set_param(param+'_item', '')
                    widget.clear()
                    for i in value:
                        item = QtGui.QTreeWidgetItem([i])
                        count = widget.topLevelItemCount()
                        item.setData(0, QtCore.Qt.UserRole,
                                     QtCore.QVariant(count))
                        widget.addTopLevelItem(item)
                    if self.model.has_param(param+'_index'):
                        idx = self.model.get_param(param+'_index')
                        if idx != -1 and idx < len(value):
                            item = widget.topLevelItem(idx)
                            widget.setCurrentItem(item)
                            widget.setItemSelected(item, True)
                            val = value[idx]
                            self.model.set_param(param+'_item', val)
                            if sender in self._callbacks:
                                self.model.set_notify(True)
                                self._callbacks[sender]()
                                self.model.set_notify(False)
                        else:
                            self.model.set_param(param+'_item', '')

                elif isinstance(widget, QtGui.QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QtGui.QFontComboBox):
                    font = widget.currentFont()
                    font.fromString(value)
                elif isinstance(widget, QtGui.QDateEdit):
                    if not value:
                        return
                    fmt = QtCore.Qt.ISODate
                    date = QtCore.QDate.fromString(value, fmt)
                    if date:
                        widget.setDate(date)
                elif isinstance(widget, QtGui.QComboBox):
                    self.model.set_param(param+'_item', '')
                    widget.clear()
                    for item in value:
                        widget.addItem(item)
                    if self.model.has_param(param+'_index'):
                        idx = self.model.get_param(param+'_index')
                        if idx != -1 and idx < len(value):
                            widget.setCurrentIndex(idx)
                            self.model.set_param(param+'_item', value[idx])
                else:
                    print('subject_changed(): Unknown widget:',
                          str(widget.objectName()), widget, value)
            self.model.set_notify(notify)

        if param not in self._actions:
            return
        widgets = []
        if param in self._model_to_view:
            for widget in self._model_to_view[param]:
                widgets.append(widget)
        # Call the model callback w/ the view's widgets as the args
        for action in self._actions[param]:
            action(*widgets)

    def refresh_view(self, *params):
        """Sends a notification message for each known model parameter."""
        if not params:
            params= tuple(self._model_to_view.keys() +
                          self._actions.keys())
        notified = []
        for param in params:
            if param not in notified:
                notified.append(param)
        self.model.notify_observers(*notified)

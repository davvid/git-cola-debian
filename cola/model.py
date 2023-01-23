# Copyright (c) 2009 David Aguilar
"""
This module provides the Model class, a generic, serializable
data container.
"""

import os
import imp
import __builtin__
from cStringIO import StringIO
from types import DictType
from types import ListType
from types import TupleType
from types import StringTypes
from types import BooleanType
from types import IntType
from types import LongType
from types import FloatType
from types import ComplexType
from types import InstanceType
from types import FunctionType

from cola import jsonpickle
from cola import observable


class Model(observable.Observable):
    """
    Model is a base class that implements convenient
    serialization methods.
    """
    def __init__(self):
        observable.Observable.__init__(self)

    def __getitem__(self, item):
        """Adds support for retrieving a parameter via model['param'].

        >>> m = Model()
        >>> m.answer = 42
        >>> m['answer']
        42

        """
        return self.__dict__[item]

    def __setitem__(self, item, value):
        """
        Adds support for setting a parameter via model['param'] = value.

        >>> m = Model()
        >>> m['answer'] = 42
        >>> m.answer
        42

        >>> m.get_answer()
        42

        >>> m.getAnswer()
        42

        """
        self.__dict__[item] = value

    def __iter__(self):
        """Provides iterator access to a model class.

        This allows you to iterate over a model's parameters as if it
        were a list.

        >>> m = Model()
        >>> m.answer = 42
        >>> key = 'nada'
        >>> for k, v in m: key = k
        >>> key
        'answer'

        >>> m = Model()
        >>> m.answer = 42
        >>> value = 'nada'
        >>> for k, v in m: value = v
        >>> value
        42

        """
        return ModelIterator(self)

    def __filter_dict(self, dct):
        """This method removes all items that begin with an underscore.

        >>> m = Model()
        >>> m._Model__filter_dict({'a': 1, '_b': 2, 'c_': 3})
        {'a': 1}

        """
        filtered = {}
        included = set([(k, v) for k, v in dct.iteritems()
                                   if k[0] != '_' and
                                      k[-1] != '_' and
                                      not k.startswith('py/')])
        for k, v in included:
            filtered[k] = v
        return filtered

    def items(self, raw=False):
        """Provides a dictionary-like items() iterator.

        >>> m = Model().from_dict(dict(a='a', b='b'))
        >>> value = 'nada'
        >>> for k, v in m.items(): value = v;
        >>> value
        'b'

        """
        if raw:
            return self.to_dict().items()
        return self.__filter_dict(self.to_dict()).items()

    def iteritems(self, raw=False):
        """Provides a dictionary-like iteritems() iterator.

        >>> m = Model().from_dict(dict(a='a', b='b'))
        >>> value = 'nada'
        >>> for k, v in m.iteritems(): value = v;
        >>> value
        'b'

        """
        if raw:
            return self.to_dict().iteritems()
        return self.__filter_dict(self.to_dict()).iteritems()

    def get_param_names(self, export=False):
        """Returns a list of serializable attribute names.

        >>> m = Model()
        >>> m._question = 'unknown'
        >>> m.answer = 42

        >>> m.get_param_names()
        ['answer']

        >>> m.get_param_names(export=True)
        ['_Observable__notify', '_Observable__observers', '_question', 'answer']

        """
        names = []
        for k, v in self.__dict__.iteritems():
            if k[0] == '_' and not export:
                continue
            if k.startswith('py/') and not export:
                continue
            if is_function(v):
                continue
            if is_atom(v) or is_list(v) or is_dict(v) or is_model(v):
                names.append(k)
        names.sort()
        return names

    def clone(self):
        """Creates a clone of the current object.

        >>> m = Model()
        >>> m.answer = 42
        >>> clone = m.clone()
        >>> clone.answer
        42

        >>> type(clone)
        <class 'cola.model.Model'>

        """
        observers = self.get_observers()
        self.set_observers([])
        clone = jsonpickle.decode(jsonpickle.encode(self))
        self.set_observers(observers)
        return clone

    def has_param(self,param):
        """Returns true if a parameter exists in a model.

        >>> m = Model()
        >>> m.answer = 42
        >>> m.has_param('answer')
        True

        >>> m.has_param('question')
        False

        """
        return param in self.__dict__

    def get_param(self, param, default=None):
        """Returns the value of a model parameter.

        >>> m = Model()
        >>> m.answer = 42
        >>> m.get_param('answer')
        42

        >>> m.get_param('another answer', 42)
        42
        """
        return self.__dict__.get(param, default)

    def __getattr__(self, param):
        """Provides automatic get/set/add/append methods.

        This provides automatic convenience methods for handling
        get/set pushups.  This method generates closures for every
        unimplemented get/set method encountered.

        >>> m = Model()
        >>> m.answer = 42
        >>> m.getAnswer()
        42

        >>> m.setAnswer(41)
        >>> m.answer
        41

        >>> m.get_answer()
        41

        >>> m.set_answer(42)
        >>> m.get_ANSWER()
        42

        >>> m.list = []
        >>> m.add_list(1)
        >>> m.list
        [1]

        >>> m.addList(2)
        >>> m.list
        [1, 2]

        >>> m.append_list(3)
        >>> m.list
        [1, 2, 3]

        >>> m.appendList(4)
        >>> m.list
        [1, 2, 3, 4]

        """

        # Base case: we actually have this param
        if param in self.__dict__:
            return getattr(self, param)

        # Check for the translated variant of the param
        realparam = self.__translate(param, sep='')
        if realparam in self.__dict__:
            return getattr(self, realparam)

        if realparam.startswith('get'):
            param = self.__translate(param, 'get')
            return lambda: getattr(self, param)

        elif realparam.startswith('set'):
            param = self.__translate(param, 'set')
            return lambda v: self.set_param(param, v,
                                            check_params=True)

        elif (realparam.startswith('add') or realparam.startswith('append')):
            if realparam[1] == 'd': # add
                param = self.__translate(param, 'add')
            else:
                param = self.__translate(param, 'append')

            def array_append_closure(*values):
                array = self.get_param(param, None)
                if array is None:
                    classname = self.__class__.__name__
                    errmsg = ("%s object has no array named '%s'"
                              % (classname, param))
                    raise AttributeError(errmsg)
                else:
                    array.extend(values)
            return array_append_closure

        errmsg  = ("%s object has no parameter '%s'"
                   % (self.__class__.__name__, param))

        raise AttributeError(errmsg)

    def set_param(self, param, value, notify=True, check_params=False):
        """Set attributes with optional validity checks.

        >>> m = Model()
        >>> m.answer = 41
        >>> m.set_param('answer', 42)
        >>> m.answer
        42

        """
        param = param.lower()
        if check_params and param not in self.get_param_names():
            raise AttributeError("Parameter '%s' not available for %s"
                                 % (param, self.__class__.__name__))
        setattr(self, param, value)
        if notify:
            self.notify_observers(param)

    def copy_params(self, model, params_to_copy=None):
        """Copies params from one model to another.

        >>> m = Model()
        >>> m.answer = 42
        >>> m._question = 'unknown'
        >>> m2 = Model()
        >>> m2.copy_params(m)
        >>> m2._question
        'unknown'

        >>> m2.answer
        42

        """
        for k in params_to_copy or model.get_param_names(export=True):
            self[k] = model.get_param(k)

    def __translate(self, param, prefix='', sep='_'):
        """Translates an param name from the external name
        used in methods to those used internally.  The default
        settings strip off '_' so that both get_foo() and getFoo()
        are valid incantations.

        >>> m = Model()
        >>> m._Model__translate('set_QUESTION', 'set')
        'question'

        """
        return param[len(prefix):].lstrip(sep).lower()

    def save(self, filename):
        """Saves a model to a file.
        """
        fh = open(filename, 'w')
        try:
            fh.write(jsonpickle.encode(self))
        except:
            pass
        fh.close()

    def load(self, filename):
        """Loads model state from a file.
        """
        fh = open(filename, 'r')
        contents = fh.read()
        fh.close()
        try:
            ddict = jsonpickle.decode(contents)
            return self.from_dict(ddict)
        except:
            pass
        return self

    @staticmethod
    def instance(filename):
        """Instances a model from a filename.
        """
        fh = open(filename, 'r')
        contents = fh.read()
        fh.close()
        obj = jsonpickle.decode(contents)
        if is_dict(obj):
            return Model().from_dict(obj)
        else:
            return obj

    def from_dict(self, source_dict):
        """Import a complex model from a dictionary.
        If it looks like a duck, it's a duck.

        >>> Model().from_dict({'answer': 42}).answer
        42
        """
        # Load parameters in-place
        unpickler = jsonpickle.unpickler.Unpickler()
        obj = unpickler.restore(source_dict)
        if is_model(obj):
            self.copy_params(obj)
        elif is_dict(obj):
            for k, v in obj.iteritems():
                self[k] = unpickler.restore(v)
        return self

    def to_dict(self):
        """
        Exports a model to a dictionary.
        This simplifies serialization.

        >>> is_dict(Model().to_dict())
        True

        """
        return jsonpickle.pickler.Pickler().flatten(self)

    __indent__ = 0
    __preindent__ = True
    __strstack__ = __builtin__.set()

    @staticmethod
    def __indent(i=0):
        Model.__indent__ += i
        return '    ' * Model.__indent__

    def __str__(self):
        """A convenient, recursively-defined stringification method."""
        # This avoid infinite recursion on cyclical structures
        if self in Model.__strstack__:
            return 'self' # TODO: implement references?  This ain't lisp.
        else:
            Model.__strstack__.add(self)
        io = StringIO()
        if Model.__preindent__:
            io.write(Model.__indent())
        io.write(self.__class__.__name__ + '(')

        Model.__indent(1)

        for param in self.get_param_names():
            if param.startswith('_'):
                continue
            io.write('\n')

            inner = Model.__indent() + param + " = "
            value = self[param]

            if type(value) == ListType:
                indent = Model.__indent(1)
                io.write(inner + "[\n")
                for val in value:
                    if is_model(val):
                        io.write(str(val)+'\n')
                    else:
                        io.write(indent)
                        io.write(str(val))
                        io.write(",\n")

                io.write(Model.__indent(-1))
                io.write("],")
            else:
                Model.__preindent__ = False
                io.write(inner)
                io.write(str(value))
                io.write(',')
                Model.__preindent__ = True

        io.write('\n' + Model.__indent(-1) + ')')
        value = io.getvalue()
        io.close()

        Model.__strstack__.remove(self)
        return value


#############################################################################
class ModelIterator(object):
    """Provides an iterator over model (key, value) pairs.
    """
    def __init__(self, model):
        self.model = model
        self.params = model.get_param_names()
        self.idx = -1
    def next(self):
        try:
            self.idx += 1
            name = self.params[self.idx]
            return (name, self.model[name])
        except IndexError:
            raise StopIteration


#############################################################################
def is_model(item):
    return issubclass(item.__class__, Model)
def is_dict(item):
    return type(item) is DictType
def is_list(item):
    return type(item) is ListType or type(item) is TupleType
def is_atom(item):
    return(type(item) in StringTypes
        or type(item) is BooleanType
        or type(item) is IntType
        or type(item) is LongType
        or type(item) is FloatType
        or type(item) is ComplexType)
def is_function(item):
    return type(item) is FunctionType

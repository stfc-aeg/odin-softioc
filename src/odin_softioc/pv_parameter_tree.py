"""parameter_tree.py - classes representing a sychronous parameter tree and accessor.

This module defines a parameter tree and accessor for use in synchronous API adapters, where
concurrency over blocking operations (e.g. to read/write the value of a parameter from hardware)
is not required.

Tim Nicholls, STFC Detector Systems Software Group.
"""
from odin.adapters.parameter_tree import (
    ParameterAccessor, ParameterTree, ParameterTreeError
)

__all__ = ['PvParameterAccessor', 'PvParameterTree', 'ParameterTreeError']


class PvParameterAccessor(ParameterAccessor):
    """Synchronous container class representing accessor methods for a parameter.

    This class extends the base parameter accessor class to support synchronous set and get
    accessors for a parameter. Read-only and writeable parameters are supported, and the same
    metadata fields are implemented.
    """

    #def __init__(self, path, getter=None, setter=None, **kwargs):
    def __init__(self, name, pv_name, setter=None, initial_value=None, param_type=None, **kwargs):
        """Initialise the ParameterAccessor instance.

        This constructor initialises the ParameterAccessor instance, storing the path of the
        parameter, its set/get accessors and setting metadata fields based on the the specified
        keyword arguments.

        :param path: path of the parameter within the tree
        :param getter: get method for the parameter, or a value if read-only constant
        :param setter: set method for the parameter
        :param kwargs: keyword argument list for metadata fields to be set; these must be from
                       the allow list specified in BaseParameterAccessor.allowed_metadata
        """

        self._name = name
        self._pv_name = pv_name
        self._value = initial_value
        self._setter = setter

        self._pv = None

        # Save the type of the parameter for type checking
        if param_type:
            self._type = param_type
        elif initial_value:
            self._type = type(param_type)
        else:
            raise ParameterTreeError(
                f"Cannot create parameter accessor {name} without type or initial value"
            )

        # Initialise the superclass with the specified arguments
        super(PvParameterAccessor, self).__init__(name, self._get, self._set, **kwargs)

        # Set the type metadata fields based on the resolved tyoe
        self.metadata["type"] = self._type.__name__

    def bind(self, builder):

        print(f"Binding PV at {self._pv_name}")
        self._pv = builder.longOut(
            self._pv_name, initial_value=self._value, on_update=self._inner_set
        )

    def _get(self):
        return self._value

    def _set(self, value):
        if self._pv:
            print(f"Updating PV {self._pv_name} with value {value}")
            self._pv.set(value)
        else:
            self._inner_set(value)

    def _inner_set(self, value):
        print(f"Inner set called for {self._name} with value {value}")
        self._value = value
        if callable(self._setter):
            self._setter(value)


class PvBoundTree(object):

    def __init__(self, name=""):

        print(f"PVBoundTree {name}: init called")
        self.__dict__["name"] = name
        self.__dict__["bound_params"] = {}

    def bind(self, name, param):

        self.bound_params[name] = param

    def __getattribute__(self, name):

        if (name != '__dict__' and
            "bound_params" in self.__dict__ and
            name in self.__dict__["bound_params"]):
            print(f"PVBoundTree {self.name}: getting bound parameter {name}")
            return self.bound_params[name].get()
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):

        if name in self.bound_params:
            print(f"PVBoundTree {self.name}: setting bound parameter {name} to {value}")
            self.bound_params[name].set(value)
        else:
            print(f"PVBoundTree {self.name}: setting unbound parameter {name} to {value}")
            super().__setattr__(name, value)


class PvParameterTree(PvBoundTree, ParameterTree):
    """Class implementing a synchronous tree of parameters and their accessors.

    This lass implements an arbitrarily-structured, recursively-managed tree of parameters
    and the appropriate accessor methods that are used to read and write those parameters.
    """

    def __init__(self, tree, builder=None):
        """Initialise the ParameterTree object.

        This constructor recursively initialises the ParameterTree object based on the specified
        arguments. The tree initialisation syntax follows that of the BaseParameterTree
        implementation.

        :param tree: dict representing the parameter tree
        :param mutable: Flag, setting the tree
        """

        # Initialise the superclass with the specified parameters
        PvBoundTree.__init__(self, name="/")
        ParameterTree.__init__(self, tree, mutable=False)

        self._builder = builder

        self._bind_tree(self._tree, self)

    def _bind_tree(self, node, subtree, path=[]):

        def join_path(p):
            return '/'.join(p)

        if isinstance(node, PvParameterAccessor):
            print(f"Binding param {node._name} PV {node._pv_name} at path {join_path(path)}")
            if self._builder:
                node.bind(self._builder)
            subtree.bind(node._name, node)

        elif isinstance(node, ParameterAccessor):
            name = path[-1] if len(path) else "/"
            print(f"Binding ParameterAccessor {name} at path {join_path(path)}")
            subtree.bind(name, node)

        elif isinstance(node, dict):
            if len(path):
                subtree_name = path[-1]
                print(f"subtree {subtree_name} at path {join_path(path)}: {node}")
                setattr(subtree, subtree_name, PvBoundTree(join_path(path)))
                subtree = getattr(subtree, subtree_name)
            for k, v in node.items():
                self._bind_tree(v, subtree, path + [k])

        else:
            print(f"Binding non-PV, non-subtree param {path[-1]} type {type(node)} at path {join_path(path)}")
            setattr(subtree, path[-1], node)

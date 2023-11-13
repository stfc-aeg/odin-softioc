"""parameter_tree.py - classes representing a sychronous parameter tree and accessor.

This module defines a parameter tree and accessor for use in synchronous API adapters, where
concurrency over blocking operations (e.g. to read/write the value of a parameter from hardware)
is not required.

Tim Nicholls, STFC Detector Systems Software Group.
"""
from odin.adapters.parameter_tree import (
    ParameterAccessor,
    ParameterTree,
    ParameterTreeError,
)

__all__ = ["PvParameterAccessor", "PvParameterTree", "ParameterTreeError"]


class PvParameterAccessor(ParameterAccessor):
    """Synchronous container class representing accessor methods for a parameter.

    This class extends the base parameter accessor class to support synchronous set and get
    accessors for a parameter. Read-only and writeable parameters are supported, and the same
    metadata fields are implemented.
    """

    out_record_types = {
        "int": "longOut",
        "float": "aOut",
        "bool": "boolOut",
        "str": "longStringOut",
    }
    in_record_types = {
        "int": "longIn",
        "float": "aIn",
        "bool": "boolIn",
        "str": "longStringIn",
    }

    def __init__(
        self,
        name,
        pv_name,
        on_get=None,
        on_set=None,
        writeable=False,
        initial_value=None,
        param_type=None,
        **kwargs,
    ):
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
        self._on_get = on_get
        self._on_set = on_set

        self._pv = None

        # Save the type of the parameter for type checking
        if param_type:
            self._type = param_type
        elif initial_value:
            self._type = type(initial_value)
        else:
            raise ParameterTreeError(
                f"Cannot create parameter accessor {name} without type or initial value"
            )

        # Initialise the superclass with the specified arguments
        super(PvParameterAccessor, self).__init__(
            name + "/", self._get, self._set, **kwargs
        )

        # Since _get and _set accessors have been passed to the superclass, the parameter will
        # be interpreted as writeable. Override this based on the specified writeable argument
        self.metadata["writeable"] = writeable

        # Set the type metadata fields based on the resolved tyoe
        self.metadata["type"] = self._type.__name__

    def bind(self, builder):
        print(f"**** Binding PV at {self._pv_name} with metadata {self.metadata}")

        builder_kwargs = {"initial_value": self._get()}
        try:
            if self.is_writeable:  # metadata["writeable"]:
                record_type = self.out_record_types[self.metadata["type"]]
                builder_kwargs["on_update"] = self._inner_set
            else:
                record_type = self.in_record_types[self.metadata["type"]]

        except KeyError:
            raise ParameterTreeError(
                f"Unable to bind PV {self._pv_name} with unsupported type {self.metadata['type']}"
            )
        print(f"     Record type is : {record_type}")
        self._pv = getattr(builder, record_type)(self._pv_name, **builder_kwargs)

    def update(self):
        if self.is_external:
            value = self._on_get()
            if value != self._value and self._pv:
                print(f"Updating PV of param {self._name} with new value {value}")
                self._pv.set(value, process=False)
            self._value = value

    @property
    def is_external(self):
        return callable(self._on_get)

    @property
    def is_writeable(self):
        return self.metadata["writeable"]

    def _get(self):
        if self.is_external:
            self._value = self._on_get()
        return self._value

    def _set(self, value):
        if self._pv:
            print(f"Setting PV {self._pv_name} to value {value}")
            self._pv.set(value)
            if not self.is_writeable:
                self._inner_set(value)
        else:
            self._inner_set(value)

    def _inner_set(self, value):
        print(f"Inner set called for {self._name} with value {value}")
        self._value = value
        if callable(self._on_set):
            self._on_set(value)


class PvBoundTree(object):
    def __init__(self, name=""):
        print(f"PVBoundTree {name}: init called")
        self.__dict__["name"] = name
        self.__dict__["bound_params"] = {}
        self.__dict__["external_params"] = []
        self.__dict__["subtrees"] = []

    def add_subtree(self, name, subtree):
        self.__dict__[name] = subtree
        self.subtrees.append(name)

    def bind(self, name, param):
        self.bound_params[name] = param

        if type(param) is PvParameterAccessor and param.is_external:
            print(f"*@*@*@ PVBoundTree {self.name}: PV param {name} is external")
            self.external_params.append(name)

        if type(param) is ParameterAccessor and callable(param._get):
            print(f"*@*@*@ PVBoundTree {self.name}: param {name} has callable get")
            self.external_params.append(name)

    def update(self, name):

        if name in self.external_params:
            if type(self.bound_params[name]) is PvParameterAccessor:
                print(f"Updating external bound param {name}")
                self.bound_params[name].update()

    def __getattribute__(self, name):
        if (
            name != "__dict__"
            and "bound_params" in self.__dict__
            and name in self.__dict__["bound_params"]
        ):
            # print(f"PVBoundTree {self.name}: getting bound parameter {name}")
            return self.bound_params[name].get()
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.bound_params:
            # print(f"PVBoundTree {self.name}: setting bound parameter {name} to {value}")
            if type(self.bound_params[name]) is PvParameterAccessor:
                self.bound_params[name]._set(value)
            else:
                self.bound_params[name].set(value)
        else:
            # print(
            #     f"PVBoundTree {self.name}: setting unbound parameter {name} to {value}"
            # )
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
        self._has_external_params = False

        self._bind_tree(self._tree, self)

    def has_external_params(self):
        return self._has_external_params

    def update_external_params(self, tree=None):
        if not tree:
            tree = self

        print(f"Update external params on subtree {tree.name}: {tree.external_params}")
        for external_param in tree.external_params:
            tree.update(external_param)

        for subtree_name in tree.subtrees:
            self.update_external_params(getattr(tree, subtree_name))

    def _bind_tree(self, node, tree, path=[]):
        def join_path(p):
            return "/".join(p)

        if isinstance(node, PvParameterAccessor):
            print(
                f"Binding param {node._name} PV {node._pv_name} at path {join_path(path)}"
            )
            if self._builder:
                node.bind(self._builder)
            tree.bind(node._name, node)

        elif isinstance(node, ParameterAccessor):
            name = path[-1] if len(path) else "/"
            print(f"Binding ParameterAccessor {name} at path {join_path(path)}")
            tree.bind(name, node)

        elif isinstance(node, dict):
            if len(path):
                subtree_name = path[-1]
                print(
                    f"\n>>>> Binding subtree {subtree_name} into parent of type {type(tree)} at path {join_path(path)}: {node}"
                )
                new_subtree = PvBoundTree(join_path(path))
                tree.add_subtree(subtree_name, new_subtree)
                tree = new_subtree
            for k, v in node.items():
                self._bind_tree(v, tree, path + [k])

        else:
            print(
                f"Binding non-PV, non-subtree param {path[-1]} type {type(node)} at path {join_path(path)}"
            )
            setattr(tree, path[-1], node)

        self._has_external_params |= bool(tree.external_params)

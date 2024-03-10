import json

from cgkit.cflow.graph import ControlFlowGraph
from loguru import logger
from functools import wraps
from pathlib import Path

from ..nodes import (
    WorkNode,
    TileIteratorBeginNode,
    TileIteratorEndNode,
)
from ..constants import (
    DEVICE_KEY,
    KEEP_KEY,
    OPSPEC_KEY,
    ORCHESTRATION_KEY,
)
from ..utils import (
    generate_op_spec,
)




class TimeStepRecipe(ControlFlowGraph):
    def __init__(self, verbose=False, **kwargs):

        super().__init__(verbose=verbose, **kwargs)

        self.interface_fnames = set()
        self.output_fnames = set()
        self.opspecs = dict()        # str: dict
        self.opspec_fnames = dict()  # str: Path(or str)

        self._log = logger

        self.__is_empty = True

    def _shallowCopy(self):
        shallowCopy = super()._shallowCopy()
        shallowCopy.opspecs = self.opspecs.copy()
        shallowCopy.opspec_fnames = self.opspec_fnames.copy()
        return shallowCopy

    def _isFirstNode(self, handle):
        if self.__is_empty:
            self.setEdgeAttribute((self.root, handle), KEEP_KEY, True)
            self.__is_empty = False

    def nodeappending(add_node):
        @wraps(add_node)
        def wrapper(self, *args, **kwargs):
            handle = add_node(self, *args, **kwargs)
            self._isFirstNode(handle)
            return handle
        return wrapper

    @nodeappending
    def add_work(self, name:str, after:int, map_to:str):
        # assuming the node name and subroutine name are the same
        fnName = name
        # assuming the subroutine name is structured as [unit_name]_[routine_name]
        #    e.g., "Hydro_advance" is belong to "Hydro" unit
        try:
            spec_name, _ = name.split("_")
        except ValueError:
            self._log.exception("Unable to decode unit name from {_name}", _name=name)
            raise ValueError
        node = WorkNode(name=fnName, opspec=spec_name)     #TODO: opspec argument may redundant
        handle = self.linkNode(node)(after)
        self.setNodeAttribute(handle, DEVICE_KEY, map_to.lower())
        self.setNodeAttribute(handle, OPSPEC_KEY, spec_name)
        # add interface files needed to be parsed
        self.interface_fnames.add(spec_name + "_interface.F90")

        self._log.info("adding WorkNode({_name})", _name=name)

        return handle

    @nodeappending
    def begin_orchestration(self, itor_type, after, **kwargs):
        node = TileIteratorBeginNode("itor", itor_type, **kwargs)
        handle = self.linkNode(node)(after)
        self.setNodeAttribute(handle, ORCHESTRATION_KEY, "begin")

        self._log.info("begin orchestration")

        return handle

    @nodeappending
    def end_orchestration(self, begin_node, after):
        begin_node_obj = self.G.nodes[begin_node]["obj"]   #TODO: cgkit.BaseGraphNetworkX.getNodeAttribute?
        node = TileIteratorEndNode(begin_node_obj)
        handle = self.linkNode(node)(after)
        self.setNodeAttribute(handle, ORCHESTRATION_KEY, "end")

        self._log.info("end orchestration of node {_node}", _node=begin_node)

        return handle

    def get_operation_spec(self, operation_name:str):
        assert operation_name in self.opspecs.keys(), (
            f"{operation_name} spec is not found in the given recipe"
        )
        return self.opspecs[operation_name]

    def get_operation_spec_fname(self, operation_name:str):
        assert operation_name in self.opspec_fnames.keys(), (
            f"{operation_name} spec is not found in the given recipe"
        )
        return self.opspec_fnames[operation_name]

    def set_output_fnames(self, fnames:set):
        self.output_fnames = set(fnames)

    def get_output_fnames(self):
        return set(self.output_fnames)

    def collect_operation_specs(self):
        """
        Generating required operation spec in JSON format
        by processing interface files recorded under self.interface_fnames.
        It also writes the JSON files on the disk.
        """
        # populate JSONs from the interface files
        for interface in self.interface_fnames:
            interface_path = Path(interface)
            if not interface_path.is_file():
                self._log.error("{_fname} is not found in the current directory", _fname=interface_path)
                raise FileNotFoundError(interface_path)
            # get operation spec name
            op_spec_name, _ = interface_path.stem.split("_")
            self._log.info(
                "Generating {_op_spec_name} operation spec" +
                " by processing {_interface_path}",
                _op_spec_name=op_spec_name,
                _interface_path=interface_path
            )
            # populate operation spec and write on disk
            op_spec_path = generate_op_spec(op_spec_name, interface_path, debug=False, call_cpp=True)
            self._log.info(
                "Operation spec is written at {_op_spec_path}",
                _op_spec_path=op_spec_path
            )
            # save operation spec data in the recipe
            with open(op_spec_path, 'r') as fptr:
                op_spec_data = json.load(fptr)
            self.opspecs.update({op_spec_name : op_spec_data})
            self.opspec_fnames.update({op_spec_name : op_spec_path})
        return



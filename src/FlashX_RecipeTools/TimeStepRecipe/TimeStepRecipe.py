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
    SETUP_OPERATION_SPEC_FNAME,
    ORCHESTRATION_KEY,
)
from ..utils import OperationSpec




class TimeStepRecipe(ControlFlowGraph):
    def __init__(self, verbose=False, **kwargs):

        super().__init__(verbose=verbose, **kwargs)

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
        try:
            spec_name, fnName = name.split("::")
        except ValueError:
            self._log.exception("name should be passed as [spec_name]::[function_name]")
            raise
        node = WorkNode(name=fnName, opspec=spec_name)     #TODO: opspec argument may redundant
        handle = self.linkNode(node)(after)
        self.setNodeAttribute(handle, DEVICE_KEY, map_to.lower())
        self.setNodeAttribute(handle, OPSPEC_KEY, spec_name)

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

    def add_group_specs(self):
        """
        Reads the file SETUP_OPERATION_SPEC_FNAME then
        reads each operation spec file and writes JSON to disk.
        """
        specs = dict()
        assert Path(SETUP_OPERATION_SPEC_FNAME).is_file(), (
            f"{SETUP_OPERATION_SPEC_FNAME} is not found in current directory"
        )
        with open(SETUP_OPERATION_SPEC_FNAME, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line.startswith("#") or len(line) == 0:
                    continue
                spec_name, spec_fname = line.split()
                if spec_name in specs.keys():
                    raise ValueError(
                        f"{spec_name} defined multiple times in file: {SETUP_OPERATION_SPEC_FNAME}"
                    )
                specs.update({spec_name: spec_fname})
        for spec_name, spec_fname in specs.items():
            opspec = OperationSpec(spec_fname)
            self._log.info(
                "Operation Spec {_spec_name} is loaded from {_spec_fname}",
                _spec_name=spec_name, _spec_fname=spec_fname
            )
            # write to json file to dick
            opspec.write2json(f"__{spec_name}.json")
            # update data
            self.opspecs.update({spec_name : opspec.data})
            self.opspec_fnames.update({spec_name : f"__{spec_name}.json"})


from __future__ import annotations

import json

from cgkit.cflow.graph import ControlFlowGraph
from loguru import logger
from functools import wraps
from pathlib import Path

from .TimeStepIR import TimeStepIR

from ._controller import (
    Ctr_InitNodeFromOpspec,
    Ctr_SetupEdge,
    Ctr_MarkEdgeAsKeep,
    Ctr_InitSubgraph,
    Ctr_ParseTFGraph,
    Ctr_ParseTFNode,
    Ctr_ParseTFMultiEdge,
)

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
    CGKIT_VERBOSITY,
)
from ..utils import (
    generate_op_spec,
)




class TimeStepRecipe(ControlFlowGraph):
    def __init__(self, flashx_objdir=".", verbose=CGKIT_VERBOSITY, **kwargs):

        super().__init__(verbose=verbose, **kwargs)

        self.objdir = Path(flashx_objdir)

        self.interface_fnames = set()
        self.output_fnames = set()
        self.opspecs = dict()        # str: dict
        self.opspec_fnames = dict()  # str: Path(or str)

        self._log = logger

        self.__is_empty = True

    def _shallowCopy(self):
        shallowCopy = super()._shallowCopy()
        shallowCopy.objdir = self.objdir
        shallowCopy.interface_fnames = self.interface_fnames.copy()
        shallowCopy.output_fnames = self.output_fnames.copy()
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

    def add_output_fnames(self, filenames_to_add:set):
        for filename in filenames_to_add:
            if filename in self.output_fnames:
                raise ValueError(f"Duplicate filename detected: {filename}")
            self.output_fnames.add(filename)

    def get_output_fnames(self):
        return set(self.output_fnames)

    def plot(self, ax=None, nodeLabels=False, edgeLabels=False):
        """
        Redefine cgkit.cflow.basegraph_networkx.BaseGraphNetworkX.plot()
        """
        import networkx as nx
        from copy import deepcopy
        from matplotlib import pyplot as plt

        if ax is None:
            ax = plt.gcf().gca()

        xmin, xmax = ax.axes.get_xlim()
        ymin, ymax = ax.axes.get_ylim()

        xsize = xmax - xmin
        ysize = ymax - ymin

        pos_nodes     = self.linear_layout(self.G, self.root)
        pos_sublabels = deepcopy(pos_nodes)
        pos_suplabels = deepcopy(pos_nodes)
        for node in pos_sublabels.keys():
            pos_sublabels[node][1] -= 0.0012*ysize
        for node in pos_suplabels.keys():
            pos_suplabels[node][1] += 0.0012*xsize

        nx.draw_networkx_nodes(self.G, pos_nodes, ax=ax, node_size=600)
        nx.draw_networkx_edges(self.G, pos_nodes,
                               ax=ax,
                               min_source_margin=15,
                               min_target_margin=15)
        nx.draw_networkx_labels(self.G, pos_nodes, ax=ax, font_size=15)
        if nodeLabels:
            labels_device = nx.get_node_attributes(self.G, 'device')
            # labels_action = deepcopy(labels_device)
            labels_name = {n:"" for n in range(len(pos_nodes))}
            for node in labels_name.keys():
                if hasattr(self.G.nodes[node]["obj"], "name"):
                    labels_name[node] = self.G.nodes[node]["obj"].name

            nx.draw_networkx_labels(self.G, pos_sublabels, ax=ax, labels=labels_device, font_size=10)
            nx.draw_networkx_labels(self.G, pos_suplabels, ax=ax, labels=labels_name, font_size=10)
        if edgeLabels:
            nx.draw_networkx_edge_labels(self.G, pos_nodes, ax=ax, font_size=10)

    def _collect_operation_specs(self):
        """
        Generating required operation spec in JSON format
        by processing interface files recorded under self.interface_fnames.
        It also writes the JSON files on the disk.
        """
        # populate JSONs from the interface files
        for interface in self.interface_fnames:
            interface_path = self.objdir / interface
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


    def compile(self) -> TimeStepIR:
        """
        Compile the recipe and returns an intermediate representation
        which contains all information for taskfunctions and dataitems
        and corresponding hierarchical graph
        """

        # collect and generate operation specs
        self._collect_operation_specs()

        # gather argument list of each nodes
        self.traverse(controllerNode=Ctr_InitNodeFromOpspec())

        # transform into hierarchical graph
        self.traverse(controllerEdge=Ctr_SetupEdge())
        h = self.extractHierarchicalGraph(
            controllerMarkEdge=Ctr_MarkEdgeAsKeep(),
            controllerInitSubgraph=Ctr_InitSubgraph()
        )

        # determine taskfunction data
        ctrParseTFGraph = Ctr_ParseTFGraph()
        ctrParseTFNode = Ctr_ParseTFNode(ctrParseTFGraph)
        ctrParseTFMultiedge = Ctr_ParseTFMultiEdge(ctrParseTFGraph)
        h.traverseHierarchy(
            controllerGraph=ctrParseTFGraph,
            controllerNode=ctrParseTFNode,
            controllerMultiEdge=ctrParseTFMultiedge
        )
        tf_data_all = list(ctrParseTFGraph.getAllTFData())

        ir = TimeStepIR()
        ir.flowGraph  = h
        ir.tf_data_all = tf_data_all

        return ir


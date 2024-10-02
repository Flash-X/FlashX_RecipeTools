import json
from loguru import logger
from copy import deepcopy

from cgkit.cflow.controller import (
    AbstractControllerNode,
    AbstractControllerEdge,
    AbstractControllerGraph,
    AbstractControllerMultiEdge,
    CtrRet,
)
from ..constants import (
    KEEP_KEY,
    DEVICE_KEY,
    DEVICE_CHANGE_KEY,
    CGKIT_VERBOSITY,
    OPSPEC_KEY,
    ORCHESTRATION_KEY,
)
from ..nodes import (
    WorkNode,
    OrchestrationBeginNode,
    OrchestrationEndNode,
    OrchestrationMarkerNode,
)


# Controllers for splitting devices form "cpu,gpu" node to "cpu" and "gpu" nodes
class Ctr_SplitDeviceGraph(AbstractControllerGraph):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger
        # mapping from original node to duplicated node
        self.node_mapping = {}
        # additional edges to be added
        self.edges_to_add = []

    def __call__(self, graph, graphAttribute):
        return CtrRet.SUCCESS

    def q(self, graph, graphAttribute):
        # adding edges
        for u, v, data in self.edges_to_add:
            graph.addEdge(u, v, **data)
        return CtrRet.SUCCESS

class Ctr_SplitDeviceNode(AbstractControllerNode):
    def __init__(self, ctrSplitDeviceGraph):
        super().__init__(controllerType="modify")
        self._log = logger
        self._ctrSplitDeviceGraph = ctrSplitDeviceGraph

    def __call__(self, graph, node, nodeAttributes):
        nodeObj = nodeAttributes["obj"]
        if isinstance(nodeObj, WorkNode):
            devices = nodeAttributes["device"]
            devices = [device.strip() for device in nodeAttributes["device"].split(',')]
            if len(devices) == 2:
                # assume the first device remains with the original node
                graph.setNodeAttribute(node, DEVICE_KEY, devices[0])
                self._ctrSplitDeviceGraph.node_mapping[node] = []

                # copy node
                newNodeDevice = devices[1]
                newNodeObj = deepcopy(nodeObj)
                newNodeHandle = graph.addNode(newNodeObj)
                # copy nodeAttributes
                for attr_key, attr_value in nodeAttributes.items():
                    graph.setNodeAttribute(newNodeHandle, attr_key, attr_value)
                graph.setNodeAttribute(newNodeHandle, DEVICE_KEY, newNodeDevice)
                self._ctrSplitDeviceGraph.node_mapping[node].append(newNodeHandle)
                self._log.info(
                    "Duplicated node {_node} to {_handle} with device={_device}",
                    _node = node,
                    _handle = newNodeHandle,
                    _device = newNodeDevice,
                )
            elif len(devices) > 2:
                raise NotImplementedError("Three devices case is not supported")

        return CtrRet.SUCCESS

class Ctr_SplitDeviceEdge(AbstractControllerEdge):
    def __init__(self, ctrSplitDeviceGraph):
        super().__init__(controllerType="modify")
        self._log = logger
        self._ctrSplitDeviceGraph = ctrSplitDeviceGraph

    def __call__(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        # Retain the original edge
        # Determine if source and/or target nodes are duplicated
        src_duplicated = srcNode in self._ctrSplitDeviceGraph.node_mapping
        trg_duplicated = trgNode in self._ctrSplitDeviceGraph.node_mapping

        # Case 1: Only target is duplicated
        if trg_duplicated and not src_duplicated:
            for duplicated_trg in self._ctrSplitDeviceGraph.node_mapping[trgNode]:
                # Preserve edge attributes by deepcopying
                new_edge_attr = deepcopy(edgeAttribute)
                self._ctrSplitDeviceGraph.edges_to_add.append(
                    (srcNode, duplicated_trg, new_edge_attr)
                )
                self._log.info(
                    "Target node ({_trgNode}) is duplicate. " +
                    "Prepared to add edge ({_srcNode}, {_duplicated_trg})",
                    _trgNode = trgNode,
                    _srcNode = srcNode,
                    _duplicated_trg = duplicated_trg,
                )

        # Case 2: Only source is duplicated
        if src_duplicated and not trg_duplicated:
            for duplicated_src in self._ctrSplitDeviceGraph.node_mapping[srcNode]:
                new_edge_attr = deepcopy(edgeAttribute)
                # NOTE: if only the source is duplicated, the edge between srcNode -- trgNode
                #       must be preserved
                edgeAttribute[KEEP_KEY] = True
                self._ctrSplitDeviceGraph.edges_to_add.append(
                    (duplicated_src, trgNode, new_edge_attr)
                )
                self._log.info(
                    "Source node ({_srcNode}) is duplicated. " +
                    "Prepared to add edge ({_duplicated_src}, {_trgNode})",
                    _srcNode = srcNode,
                    _trgNode = trgNode,
                    _duplicated_src = duplicated_src,
                )

        # Case 3: Both source and target are duplicated
        if src_duplicated and trg_duplicated:
            for duplicated_src in self._ctrSplitDeviceGraph.node_mapping[srcNode]:
                for duplicated_trg in self._ctrSplitDeviceGraph.node_mapping[trgNode]:
                    new_edge_attr = deepcopy(edgeAttribute)
                    self._ctrSplitDeviceGraph.edges_to_add.append(
                        (duplicated_src, duplicated_trg, new_edge_attr)
                    )
                    self._log.info(
                        "Both the source ({_srcNode}) and target ({_trgNode} " +
                        "nodes are duplicated. " +
                        "Prepared to add edge ({_duplicated_src}, {_duplicated_trg})",
                        _srcNode = srcNode,
                        _trgNode = trgNode,
                        _duplicated_src = duplicated_src,
                        _duplicated_trg = duplicated_trg,
                    )

        return CtrRet.SUCCESS



class Ctr_InitNodeFromOpspec(AbstractControllerNode):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger

    def __call__(self, graph, node, nodeAttributes):
        nodeObj = nodeAttributes["obj"]

        if isinstance(nodeObj, WorkNode):
            name = nodeObj.name
            operation_name = nodeAttributes[OPSPEC_KEY]
            opspec = graph.get_operation_spec(operation_name)
            try:
                args = opspec[nodeObj.name]["argument_list"]
            except KeyError:
                self._log.error(
                    "argument_list of WorkNode {_name} is not found in the operation spec",
                    _name=name
                )
                raise KeyError(name)
            self._log.info(
                "inserting argument list {_args} into WorkNode {_name}",
                _args=args,
                _name=name
            )

            setattr(nodeObj, "args", args)

        return CtrRet.SUCCESS

class Ctr_AddOrchMarkers(AbstractControllerEdge):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger

    def __call__(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        assert "obj" in srcAttribute, srcAttribute.keys()
        assert "obj" in trgAttribute, trgAttribute.keys()

        if isinstance(srcAttribute["obj"], OrchestrationBeginNode) or isinstance(
            trgAttribute["obj"], OrchestrationEndNode
        ):
            self._log.info(
                "inserting a marker between {srcNode} and {trgNode}",
                srcNode=srcAttribute["obj"].name,
                trgNode=trgAttribute["obj"].name
            )
            markerObj = OrchestrationMarkerNode()
            marker = graph.addNode(markerObj)
            graph.addEdge(srcNode, marker)
            graph.addEdge(marker, trgNode)

    def q(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        if isinstance(srcAttribute["obj"], OrchestrationBeginNode) or isinstance(
            trgAttribute["obj"], OrchestrationEndNode
        ):
            graph.G.remove_edge(srcNode, trgNode)



class Ctr_SetupEdge(AbstractControllerEdge):
    def __init__(self):
        super().__init__(controllerType="view")
        self._log = logger

    def __call__(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        assert "obj" in srcAttribute, srcAttribute.keys()
        assert "obj" in trgAttribute, trgAttribute.keys()
        if (
            isinstance(srcAttribute["obj"], WorkNode)
            and isinstance(trgAttribute["obj"], WorkNode)
            and DEVICE_KEY in srcAttribute
            and DEVICE_KEY in trgAttribute
        ):
            deviceChangeVal = srcAttribute[DEVICE_KEY] != trgAttribute[DEVICE_KEY]
            graph.setEdgeAttribute((srcNode, trgNode), DEVICE_CHANGE_KEY, deviceChangeVal)
        elif isinstance(srcAttribute["obj"], OrchestrationMarkerNode) and isinstance(
            trgAttribute["obj"], WorkNode
        ):
            # KEEP_KEY = False for edges between MakerNode -- WorkNode
            graph.setEdgeAttribute((srcNode, trgNode), KEEP_KEY, False)
        elif isinstance(srcAttribute["obj"], WorkNode) and isinstance(
            trgAttribute["obj"], OrchestrationMarkerNode
        ):
            # KEEP_KEY = False for edges between MakerNode -- WorkNode
            graph.setEdgeAttribute((srcNode, trgNode), KEEP_KEY, False)
        else:
            # otherwise, keep the edge
            graph.setEdgeAttribute((srcNode, trgNode), KEEP_KEY, True)
        return CtrRet.SUCCESS


class Ctr_GetAttributesForSubgraph(AbstractControllerNode):
    def __init__(self, verbose=CGKIT_VERBOSITY):
        super().__init__(controllerType="view")
        self._log = logger
        self.attribute = dict()
        self.workArgs = dict()
        self.opSpecs = dict()

    def __call__(self, graph, node, nodeAttribute):
        # get device(s)
        if DEVICE_KEY in nodeAttribute:
            if DEVICE_KEY not in self.attribute:
                self.attribute[DEVICE_KEY] = nodeAttribute[DEVICE_KEY]
            elif nodeAttribute[DEVICE_KEY] not in self.attribute[DEVICE_KEY]:
                self.attribute[DEVICE_KEY] = ",".join(
                    [self.attribute[DEVICE_KEY], nodeAttribute[DEVICE_KEY]]
                )
        # gather names of operation spec
        if OPSPEC_KEY in nodeAttribute:
            self.opSpecs[nodeAttribute["obj"].name] = nodeAttribute[OPSPEC_KEY]

        # get arguments of work nodes
        if isinstance(nodeAttribute["obj"], WorkNode):
            assert nodeAttribute["obj"].name not in self.workArgs
            self.workArgs[nodeAttribute["obj"].name] = nodeAttribute["obj"].args
        return CtrRet.SUCCESS

    def getAllWorkNames(self):
        allNames = set()
        for name in self.workArgs.keys():
            allNames.add(name)
        allNames = list(allNames)
        allNames.sort()
        return allNames

    def getAllWorkArgs(self):
        allArgs = set()
        for args in self.workArgs.values():
            allArgs = allArgs.union(set(args))
        allArgs = list(allArgs)
        allArgs.sort()
        return allArgs

    def getAllOpSpecs(self):
        allOpSpecs = set()
        for opspec in self.opSpecs.values():
            allOpSpecs.add(opspec)
        allOpSpecs = list(allOpSpecs)
        allOpSpecs.sort()
        return allOpSpecs


class Ctr_MarkEdgeAsKeep(AbstractControllerEdge):
    def __init__(self, verbose=CGKIT_VERBOSITY):
        super().__init__(controllerType="view")
        self._log = logger

    def __call__(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        # keep edge in coarse graph
        if KEEP_KEY in edgeAttribute:
            if edgeAttribute[KEEP_KEY]:
                return CtrRet.SUCCESS
            else:
                return CtrRet.VOID
        # allow edge for subgraph condensation
        if DEVICE_CHANGE_KEY in edgeAttribute and not edgeAttribute[DEVICE_CHANGE_KEY]:
            return CtrRet.VOID
        # otherwise keep edge in coarse graph
        return CtrRet.SUCCESS


class Ctr_InitSubgraph(AbstractControllerGraph):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger

    def __call__(self, graph, graphAttribute):
        # get info from nodes of subgraph
        ctrNode = Ctr_GetAttributesForSubgraph()
        graph.visit(controllerNode=ctrNode)
        ctrNode.attribute["names"] = ctrNode.getAllWorkNames()
        ctrNode.attribute["args"] = ctrNode.getAllWorkArgs()
        ctrNode.attribute["opspecs"] = ctrNode.getAllOpSpecs()
        ctrNode.attribute["objdir"] = graph.objdir
        ctrNode.attribute["tf_name"] = ""     # NOTE: tf_name will be determined later
        # set attributes of subgraph
        self._log.info("set subgraph level={level}, attributes={attribute}", level=graph.level, attribute=ctrNode.attribute)
        for key, val in ctrNode.attribute.items():
            graph.setGraphAttribute(key, val)
        return CtrRet.SUCCESS


class Ctr_ParseTFGraph(AbstractControllerGraph):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger
        self.tfData = list()
        self.call_graph = list()
        self.concurrent_call_graph = list()
        self.inConcurrent = False
        self.taskfn_basenm = "taskfn"
        self.taskfn_n = 0

    def __call__(self, graph, graphAttribute):
        self._log.info("parsing TF graph at level={level}", level=graph.level)
        if graph.isSubgraph():
            # clear the call graphs
            self.call_graph.clear()
            self.concurrent_call_graph.clear()
            # entering subgraph
            self._log.info("entering subgraph level={level}", level=graph.level)
            if graph.level > 0 and graph.leaf:    # TODO: need to know why this is needed
                objdir = graphAttribute["objdir"]
                device = graphAttribute["device"]
                subroutines = graphAttribute["names"]
                opspecs = graphAttribute["opspecs"]
                opspec_fnames = list()
                # get paths for required json files
                for opspec in opspecs:
                    opspec_fnames.append(graph.get_operation_spec_fname(opspec))
                if len(device.split(",")) > 1:
                    raise RuntimeError(
                        f"Multiple devices are detected in a subgraph containing {subroutines}"
                    )
                self._log.info("generating TF call graph for {_subroutines}", _subroutines=subroutines)

                tf = self._initTFData(objdir, subroutines, opspec_fnames, device)
                # save taskfunction name to subsubgraph
                # NOTE: this will be copied to the upper level subgraph attribute
                #       in the "Ctr_InitSubRootNode" controller
                graphAttribute["tf_name"] = tf["name"]

                self.tfData.append(tf)
        return CtrRet.SUCCESS


    def q(self, graph, graphAttribute):
        self._log.info("exiting subgraph level={level}", level=graph.level)
        # push call graph to TFspec
        if graph.level > 0 and graph.leaf:    # TODO: need to know why this is needed
            self.getCurrentTF()["subroutine_call_graph"] = list(self.getCallGraph())
        return CtrRet.SUCCESS

    def getCurrentTF(self):
        assert len(self.tfData)
        return self.tfData[-1]

    def getCallGraph(self):
        if self.inConcurrent:
            return self.concurrent_call_graph
        else:
            return self.call_graph

    def getAllTFData(self):
        return list(self.tfData)

    def dumpTFData(self):
        for tf in self.tfData:
            fname = f"__{tf['name']}.json"
            with open(fname, "w") as f:
                json.dump(tf, f, indent=2)


    def _initTFData(self, objdir:str, subroutines:list, opspec:list, device:str):
        tf = dict()
        tf["objdir"] = objdir
        tf["name"] = f"{device}_{self.taskfn_basenm}_{self.taskfn_n}"
        self.taskfn_n += 1
        tf["language"] = "Fortran"
        tf["variable_index_base"] = 1
        tf["processor"] = device
        tf["operation_specs"] = opspec
        tf["subroutines"] = list(subroutines)
        tf["subroutine_call_graph"] = list()

        return tf



class Ctr_ParseTFNode(AbstractControllerNode):
    def __init__(self, ctrParseGraph):
        super().__init__(controllerType="view")
        self.__ctrParseGraph = ctrParseGraph
        self._log = logger

    def __call__(self, graph, node, nodeAttribute):
        nodeObj = nodeAttribute["obj"]
        if OPSPEC_KEY in nodeAttribute:
            self.__ctrParseGraph.getCallGraph().append(nodeObj.name)




class Ctr_ParseTFMultiEdge(AbstractControllerMultiEdge):
    def __init__(self, ctrParseGraph):
        super().__init__(controllerType="view")
        self._log = logger
        self.__ctrParseGraph = ctrParseGraph

    def __call__(self, graph, node, nodeAttribute, successors):
        self._log.info("entering multiedge at node = {_node}", _node=node)
        self.__ctrParseGraph.inConcurrent = True

    def q(self, graph, node, nodeAttribute, predecessors):
        self._log.info("exiting multiedge at node = {_node}", _node=node)
        self.__ctrParseGraph.call_graph.append(
            self.__ctrParseGraph.concurrent_call_graph
        )
        self.__ctrParseGraph.inConcurrent = False


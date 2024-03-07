import json
from loguru import logger

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
    VERBOSE_DEFAULT,
    OPSPEC_KEY,
    ORCHESTRATION_KEY,
)
from ..nodes import (
    WorkNode,
)


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
        else:
            graph.setEdgeAttribute((srcNode, trgNode), KEEP_KEY, True)
        return CtrRet.SUCCESS


class Ctr_GetAttributesForSubgraph(AbstractControllerNode):
    def __init__(self, verbose=VERBOSE_DEFAULT):
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
    def __init__(self, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view")
        self._log = logger

    def __call__(self, graph, srcNode, srcAttribute, trgNode, trgAttribute, edgeAttribute):
        # keep edge in coarse graph
        if KEEP_KEY in edgeAttribute and edgeAttribute[KEEP_KEY]:
            return CtrRet.SUCCESS
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
        ctrNode = Ctr_GetAttributesForSubgraph(verbose=self.verbose)
        graph.visit(controllerNode=ctrNode)
        ctrNode.attribute["names"] = ctrNode.getAllWorkNames()
        ctrNode.attribute["args"] = ctrNode.getAllWorkArgs()
        ctrNode.attribute["opspecs"] = ctrNode.getAllOpSpecs()
        # set attributes of subgraph
        self._log.info("set subgraph attributes={attribute}", attribute=ctrNode.attribute)
        for key, val in ctrNode.attribute.items():
            graph.setGraphAttribute(key, val)
        return CtrRet.SUCCESS


class Ctr_ParseTFGraph(AbstractControllerGraph):
    def __init__(self):
        super().__init__(controllerType="view")
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
            if graph.level > 1:    # TODO: need to know why this is needed
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

                tf = self._initTFData(subroutines, opspec_fnames, device)

                self.tfData.append(tf)
        return CtrRet.SUCCESS


    def q(self, graph, graphAttribute):
        self._log.info("exiting subgraph level={level}", level=graph.level)
        # push call graph to TFspec
        if graph.level > 1:    # TODO: need to know why this is needed
            self.getCurrentTF()["subroutine_call_graph"] = list(self.call_graph)
        return CtrRet.SUCCESS

    def getCurrentTF(self):
        assert len(self.tfData)
        return self.tfData[-1]

    def getCallGraph(self):
        if self.inConcurrent:
            return self.concurrent_call_graph
        else:
            return self.call_graph

    def getTFData(self):
        return list(self.tfData)

    def dumpTFData(self):
        for tf in self.tfData:
            fname = f"__{tf['name']}.json"
            with open(fname, "w") as f:
                json.dump(tf, f, indent=2)


    def _initTFData(self, subroutines:list, opspec:list, device:str):
        tf = dict()
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


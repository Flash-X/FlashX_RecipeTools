import json
from cgkit.cflow.controller import (
    AbstractControllerNode,
    AbstractControllerEdge,
    AbstractControllerGraph,
    AbstractControllerMultiEdge,
    CtrRet,
)
from ..constants import (
    VERBOSE_DEFAULT,
    OPSPEC_KEY,
)
from ..nodes import (
    WorkNode,
)


class Ctr_InitNodeFromOpspec(AbstractControllerNode):
    def __init__(self, verbose=VERBOSE_DEFAULT):
        super().__init__(
            controllerType="modify",
            verbose=verbose,
            verbose_prefix="[Ctr_InitNodeFromOpspec]",
        )

    def __call__(self, graph, node, nodeAttributes):
        nodeObj = nodeAttributes["obj"]

        if isinstance(nodeObj, WorkNode):
            operation_name = nodeAttributes[OPSPEC_KEY]
            opspec = graph.get_operation_spec(operation_name)
            try:
                args = opspec[nodeObj.name]["argument_list"]
            except KeyError:
                raise KeyError(
                    f"argument_list of WorkNode {nodeObj.name} is not found in the operation spec"
                )
            if self.verbose:
                print(self.verbose_prefix, f"Insert argument list {args} into WorkNode {nodeObj.name}")
            setattr(nodeObj, "args", args)

        return CtrRet.SUCCESS


class Ctr_ParseTFGraph(AbstractControllerGraph):
    def __init__(self, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFGraph]")
        self.tfData = list()
        self.call_graph = list()
        self.concurrent_call_graph = list()
        self.inConcurrent = False
        self.taskfn_basenm = "taskfn"
        self.taskfn_n = 0

    def __call__(self, graph, graphAttribute):
        if self.verbose:
            print(self.verbose_prefix, f"Parsing TF graph at level={graph.level}")
        if graph.isSubgraph():
            if self.verbose:
                print(self.verbose_prefix, f"Entering subgraph level={graph.level}")
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
                if self.verbose:
                    print(self.verbose_prefix, f"Generating TF call graph for {subroutines}")

                tf = self._initTFspec(subroutines, opspec_fnames, device)

                self.tfData.append(tf)


    def q(self, graph, graphAttribute):
        if self.verbose:
            print(self.verbose_prefix, f"exiting subgraph level={graph.level}")
        # push call graph to TFspec
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

    def dumpTFData(self, **kwargs):
        for tf in self.tfData:
            fname = f"__{tf['name']}.json"
            with open(fname, "w") as f:
                json.dump(tf, f, **kwargs)


    def _initTFspec(self, subroutines:list, opspec:list, device:str):
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
    def __init__(self, ctrParseGraph, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFNode]")
        self.__ctrParseGraph = ctrParseGraph

    def __call__(self, graph, node, nodeAttribute):
        if self.verbose:
            print(self.verbose_prefix, f"parsing node = {node}, {nodeAttribute['obj'].type}")
        nodeObj = nodeAttribute["obj"]
        if OPSPEC_KEY in nodeAttribute:
            self.__ctrParseGraph.getCallGraph().append(nodeObj.name)




class Ctr_ParseTFMultiEdge(AbstractControllerMultiEdge):
    def __init__(self, ctrParseGraph, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFMultiEdge]")
        self.__ctrParseGraph = ctrParseGraph

    def __call__(self, graph, node, nodeAttribute, successors):
        if self.verbose:
            print(self.verbose_prefix, f"entering multiedge at node = {node}")
        self.__ctrParseGraph.inConcurrent = True

    def q(self, graph, node, nodeAttribute, predecessors):
        if self.verbose:
            print(self.verbose_prefix, f"exiting multiedge at node = {node}")
        self.__ctrParseGraph.call_graph.append(
            self.__ctrParseGraph.concurrent_call_graph
        )
        self.__ctrParseGraph.inConcurrent = False

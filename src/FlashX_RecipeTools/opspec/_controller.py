import json
from cgkit.cflow.controller import (
    AbstractControllerNode,
    AbstractControllerEdge,
    AbstractControllerGraph,
    AbstractControllerMultiEdge,
    CtrRet,
)
from ..constants import (
    DEVICE_KEY,
    DEVICE_DEFAULT,
    DEVICE_CHANGE_KEY,
    KEEP_KEY,
    VERBOSE_DEFAULT,
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
        opspec = graph.opspec["operation"]
        nodeObj = nodeAttributes["obj"]

        if isinstance(nodeObj, WorkNode):
            try:
                args = opspec[nodeObj.name]["argument_list"]
            except KeyError:
                raise KeyError(
                        "argument_list of WorkNode {nodeObj.name} is not found in the operation spec"
                    )
            if self.verbose:
                print(self.verbose_prefix, f"Insert argument list {args} into WorkNode {nodeObj.name}")
            setattr(nodeObj, "args", args)

        return CtrRet.SUCCESS


class Ctr_ParseTFGraph(AbstractControllerGraph):
    def __init__(self, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFGraph]")
        self.tfSpecs = list()
        self.tfSubroutines = list()
        self.taskfn_basenm = "taskfn"
        self.taskfn_n = 0

    def __call__(self, graph, graphAttribute):
        if self.verbose:
            print(self.verbose_prefix, f"Parsing TF graph at level={graph.level}")
        if graph.isSubgraph():
            if self.verbose:
                print(self.verbose_prefix, f"Entering subgraph level={graph.level}")
            if graph.level > 1:    # TODO: need to know why this is needed
                print(f"{graphAttribute['names']}, {graphAttribute['device']}")
                assert isinstance(graphAttribute['device'], str), (
                    f"Multiple devices are detected in a subgraph containing {graphAttribute['names']}"
                )
                opspec = graph.opspec
                device = graphAttribute["device"]
                args = graphAttribute["args"]
                subroutines = graphAttribute["names"]

                tfspec = self._initTFspec(opspec, device)
                args, argspecs = self._getArgsAndArgSpecs(opspec, subroutines)
                tfspec["task_function"]["argument_list"] = args    # TODO: "lbound"s ?
                tfspec["task_function"]["argument_specifications"] = argspecs

                self.tfSpecs.append(tfspec)
                self.tfSubroutines.append(subroutines)


    def q(self, graph, graphAttribute):
        print(f"exiting subgraph level={graph.level}")
        return CtrRet.SUCCESS

    def dumpTFspecs(self, **kwargs):
        for tfspec in self.tfSpecs:
            fname = f"__{tfspec['task_function']['name']}.json"
            with open(fname, "w") as f:
                json.dump(tfspec, f, **kwargs)


    def _initTFspec(self, opspec, device):
        d = dict()
        d["format"] = opspec["format"]
        d["grid"] = opspec["grid"]

        tf = dict()
        tf["name"] = f"{device}_{self.taskfn_basenm}_{self.taskfn_n}"
        self.taskfn_n += 1
        tf["language"] = "Fortran"
        tf["processor"] = device
        tf["variable_index_base"] = opspec["operation"]["variable_index_base"]

        d["task_function"] = tf

        return d

    def _getArgsAndArgSpecs(self, opspec, subroutines):
        argspecs = dict()
        args = list()
        for subroutine in subroutines:
            assert subroutine in opspec["operation"].keys()
            argspecs_from_opspec = opspec["operation"][subroutine]["argument_specifications"]
            for var, spec in argspecs_from_opspec.items():
                if var in args:
                    if spec != argspecs[var]:     # if duplicated variable detected, but different spec
                        if spec["source"] == "grid_data":
                            pass
                            #TODO: concat!!
                        else:
                            n = 0
                            newVarName = var
                            while newVarName in args:
                                n += 1
                                newVarName = f"{var}_{n}"
                            argspecs.update({newVarName:spec})
                            args.append(newVarName)
                else:
                    argspecs.update({var:spec})
                    args.append(var)

        return args, argspecs


class Ctr_ParseTFNode(AbstractControllerNode):
    def __init__(self, ctrParseGraph, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFNode]")

    def __call__(self, graph, node, nodeAttribute):
        print(f"parsing node = {node}, {nodeAttribute['obj'].type}")




class Ctr_ParseTFMultiEdge(AbstractControllerMultiEdge):
    def __init__(self, ctrParseGraph, verbose=VERBOSE_DEFAULT):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseTFMultiEdge]")

    def __call__(self, graph, node, nodeAttribute, successors):
        print(f"entering multiedge at node = {node}")

    def q(self, graph, node, nodeAttribute, predecessors):
        print(f"exiting multiedge at node = {node}")

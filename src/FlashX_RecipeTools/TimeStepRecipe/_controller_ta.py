from loguru import logger

from cgkit.cflow.controller import (
    AbstractControllerNode,
    CtrRet,
)


class Ctr_InitSubRootNode(AbstractControllerNode):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._log = logger

    def __call__(self, graph, node, nodeAttributes):
        nodeObj = nodeAttributes["obj"]
        if graph.nodeHasSubgraph(node):
            sGraph = graph.nodeGetSubgraph(node)
            subGraphAttributes = sGraph.G.graph
            assert isinstance(subGraphAttributes, dict), type(subGraphAttributes)

            print(subGraphAttributes["tfname"])
            nodeObj.name = subGraphAttributes["tfname"]

        return CtrRet.SUCCESS

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

            # the actual information for the taskfunction lies in the sub"sub"graph
            # as the cgkit generates two-level subgraph.
            ssGraph = sGraph.nodeGetSubgraph(sGraph.root)
            subsubGraphAttributes = ssGraph.G.graph

            assert isinstance(subGraphAttributes, dict), type(subGraphAttributes)
            assert isinstance(subsubGraphAttributes, dict), type(subsubGraphAttributes)

            # bringing the taskfunction name from sub"sub"graph to subgraph.
            nodeObj.name = subsubGraphAttributes["tfname"]

        return CtrRet.SUCCESS

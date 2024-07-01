from cgkit.cflow.node import (
    RootNode,
    WorkNode,
    LeafNode,
    AbstractNode,
    ClusterBeginNode,
    ClusterEndNode,
    PlainCodeNode
)


def construct_begin_end_nodes(name, tpl, startswith="", endswith=""):
    beginNode = GenericBeginNode(name, tpl, startswith=startswith, endswith=endswith)
    endNode = GenericEndNode(name, beginNode)

    return beginNode, endNode


class WorkNode(WorkNode):
    def __init__(self, startswith="", endswith="", opspec="", **kwargs):
        super().__init__(**kwargs)
        self.startswith = startswith
        self.endswith = endswith
        self.opspec = opspec


class LeafNode(LeafNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "leaf"


class SetupNode(PlainCodeNode):
    def __init__(self, name:str, tpl:str, startswith="", endswith="", **kwargs):
        super().__init__(nodeType="SetupNode", **kwargs)
        assert isinstance(name, str), type(name)
        self.name = name
        self.tpl = tpl
        self.startswith = startswith
        self.endswith = endswith


class GenericBeginNode(ClusterBeginNode):
    def __init__(self, name:str, tpl:str, startswith="", endswith="", **kwargs):
        super().__init__(nodeType="BeginNode")
        self.name = name
        self.tpl = tpl
        self.startswith = startswith
        self.endswith = endswith
        self.returnStackKey = ""


class GenericEndNode(ClusterEndNode):
    def __init__(self, name, beginNode=None):
        super().__init__(clusterBeginNode=beginNode, nodeType="EndNode")
        self.name = name


class TileIteratorBeginNode(ClusterBeginNode):
    def __init__(self, itorVar, itorType, **kwargs):
        super().__init__(nodeType="TileBeginNode")
        self.name = "tile_begin"
        self.itorVar = itorVar
        self.itorType = itorType
        self.itorOptions = kwargs
        self.returnStackKey = ""

class TileIteratorEndNode(ClusterEndNode):
    def __init__(self, beginNode=None):
        super().__init__(clusterBeginNode=beginNode, nodeType="TileEndNode")
        self.name = "tile_end"


class OrchestrationBeginNode(AbstractNode):
    def __init__(self, orchestrationEndNode=None, **kwargs):
        kwargs.setdefault("nodeType", "OrchestrationBegin")
        super().__init__(**kwargs)
        self.name = "orch_begin"
        self.endNode = list()
        if orchestrationEndNode is not None:
            self.appendEndNode(orchestrationEndNode)
            orchestrationEndNode.setBeginNode(self)

    def appendEndNode(self, orchestrationEndNode):
        assert issubclass(type(orchestrationEndNode), OrchestrationEndNode), type(orchestrationEndNode)
        self.endNode.append(orchestrationEndNode)

class OrchestrationEndNode(AbstractNode):
    def __init__(self, orchestrationBeginNode=None, **kwargs):
        kwargs.setdefault("nodeType", "OrchestrationEnd")
        super().__init__(**kwargs)
        self.name = "orch_end"
        if orchestrationBeginNode is not None:
            self.setBeginNode(orchestrationBeginNode)
            orchestrationBeginNode.appendEndNode(self)

    def getBeginNode(self):
        return self.beginNode

    def setBeginNode(self, orchestrationBeginNode):
        assert issubclass(type(orchestrationBeginNode), OrchestrationBeginNode), type(orchestrationBeginNode)
        self.beginNode = orchestrationBeginNode

    def hasBeginNode(self, orchestrationBeginNode):
        assert issubclass(type(orchestrationBeginNode), OrchestrationBeginNode), type(orchestrationBeginNode)
        return orchestrationBeginNode is self.beginNode



class OrchestrationMarkerNode(AbstractNode):
    """
    This is a fake node for marking orchestration begin and end
    """
    def __init__(self, **kwargs):
        kwargs.setdefault("nodeType", "OrchestrationMarker")
        super().__init__(**kwargs)
        self.name = "_marker_"


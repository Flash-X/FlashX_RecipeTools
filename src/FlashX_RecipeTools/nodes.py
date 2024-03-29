from cgkit.cflow.node import (WorkNode,
                              LeafNode,
                              AbstractNode,
                              ClusterBeginNode,
                              ClusterEndNode,
                              PlainCodeNode)


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
        self.name = "tile"
        self.itorVar = itorVar
        self.itorType = itorType
        self.itorOptions = kwargs
        self.returnStackKey = ""

class TileIteratorEndNode(ClusterEndNode):
    def __init__(self, beginNode=None):
        super().__init__(clusterBeginNode=beginNode, nodeType="TileEndNode")
        self.name = "tile"


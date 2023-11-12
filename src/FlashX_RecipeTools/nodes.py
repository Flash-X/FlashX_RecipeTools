from cgkit.cflow.node import (WorkNode,
                              LeafNode,
                              AbstractNode,
                              ClusterBeginNode,
                              ClusterEndNode,
                              PlainCodeNode)

class WorkNode(WorkNode):
    def __init__(self, opspec:str, **kwargs):
        super().__init__(**kwargs)
        self.opspec = opspec
        kwargs.setdefault("startswith", "")
        kwargs.setdefault("endswith", "")
        self.startswith = kwargs["startswith"]
        self.endswith = kwargs["endswith"]


class LeafNode(LeafNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SetupNode(PlainCodeNode):
    def __init__(self, name:str, tpl:str, **kwargs):
        super().__init__(nodeType="SetupNode", **kwargs)
        assert isinstance(name, str), type(name)
        self.name = name
        self.tpl = tpl
        kwargs.setdefault("startswith", "")
        kwargs.setdefault("endswith", "")
        self.startswith = kwargs["startswith"]
        self.endswith = kwargs["endswith"]


class genericBeginNode(ClusterBeginNode):
    def __init__(self, name:str, tpl:str, **kwargs):
        super().__init__(nodeType="BeginNode")
        self.name = name
        self.tpl = tpl
        kwargs.setdefault("startswith", "")
        kwargs.setdefault("endswith", "")
        self.startswith = kwargs["startswith"]
        self.endswith = kwargs["endswith"]
        self.returnStackKey = ""


class genericEndNode(ClusterEndNode):
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




## TODO
class loopBeginNode(ClusterBeginNode):
    def __init__(self, loopVar, loopRange):
        super().__init__(nodeType="LoopBeginNode")
        self.loopVar = loopVar

        assert isinstance(loopRange, list), type(loopRange)
        if len(loopRange) == 3:
            start, end, step = loopRange
        elif len(loopRange) == 2:
            start, end = loopRange
            step = None
        else:
            raise ValueError("Not a valid loopRange")
        assert isinstance(start, str), type(start)
        assert isinstance(end, str), type(end)
        assert isinstance(step, str) or step is None, type(step)
        self.start = start
        self.end = end
        self.step = step


class loopEndNode(ClusterEndNode):
    def __init__(self, name, beginNode=None):
        super().__init__(clusterBeginNode=beginNode, nodeType="LoopEndNode")
        self.name = name

from cgkit.cflow.node import WorkNode
from cgkit.cflow.node import (AbstractNode,
                              ClusterBeginNode,
                              ClusterEndNode,
                              PlainCodeNode)

class SetupNode(PlainCodeNode):
    def __init__(self, name, tpl, **kwargs):
        super().__init__(nodeType="SetupNode", **kwargs)
        assert isinstance(name, str), type(name)
        self.name = name
        self.tpl = tpl


class genericBeginNode(ClusterBeginNode):
    def __init__(self, name, tpl):
        super().__init__(nodeType="BeginNode")
        self.name = name
        self.tpl = tpl
        self.returnStackKey = ""


class genericEndNode(ClusterEndNode):
    def __init__(self, name, beginNode=None):
        super().__init__(clusterBeginNode=beginNode, nodeType="EndNode")
        self.name = name




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

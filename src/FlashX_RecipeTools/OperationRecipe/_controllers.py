from pathlib import Path
from copy import deepcopy

from cgkit.cflow.controller import (
    AbstractControllerNode,
    AbstractControllerEdge,
    AbstractControllerGraph,
    AbstractControllerMultiEdge,
    CtrRet,
)
from cgkit.ctree.srctree import SourceTree
import cgkit.ctree.srctree as srctree

from ..nodes import (
    WorkNode,
    SetupNode,
    GenericBeginNode,
    GenericEndNode,
)
from ..constants import (
    CGKIT_VERBOSITY,
)


FLASHX_RECIPETOOLS_ROOT = Path(__file__).parent.absolute()
INTERNAL_TEMPLATE_PATH = FLASHX_RECIPETOOLS_ROOT / "_internal_tpl"


class Ctr_initRecipeNode(AbstractControllerNode):
    def __init__(self, verbose=CGKIT_VERBOSITY):
        super().__init__(
            controllerType="modify",
            verbose=verbose,
            verbose_prefix="[Ctr_initRecipeNode]",
        )

    def __call__(self, graph, node, nodeAttributes):
        return CtrRet.SUCCESS

#---------------------
#-Parsing
#---------------------


def _insertConnectors(ctrParseGraph, tree, verbose=False, verbose_prefix="[_insertConnectors]"):
    stree = ctrParseGraph.getSourceTree()
    split = srctree.split_connectors(tree)
    pathInfo = dict()
    pathList = dict()
    for t in split:
        connKey = srctree.search_connectors(t).pop()
        linkKey = srctree.convert_key_from_connector_to_link(connKey)  # <_connector:KEY> => <_link:KEY>
        linkPath = ctrParseGraph.getSourceTreePath(linkKey)
        if verbose:
            print(verbose_prefix, f'Insert connector "{connKey}" at path={linkPath}')
        pathList = stree.link(t, linkPath)  # ylee: should return a dict()
        if pathList:
            pathInfo[connKey] = pathList  # ylee: where the pathInfo goes?
        else:
            assert pathList  ###DEV### TODO remove after handling CtrRet.ERROR, below
            return CtrRet.ERROR, dict()
    return CtrRet.SUCCESS, pathList


def _encloseConnector(tree, startswith, endswith):

    # TODO: other (multiple) connectors?
    assert isinstance(startswith, str), type(startswith)
    assert isinstance(endswith, str), type(endswith)
    assert "_connector:execute" in tree.keys()

    if not startswith.strip() and not endswith.strip():
        return tree

    tree = deepcopy(tree)

    execute = tree["_connector:execute"]
    if startswith.strip():
        execute["_code"].insert(0, startswith)
    if endswith.strip():
        execute["_code"].append(endswith)

    return tree

class Ctr_ParseGraph(AbstractControllerGraph):
    def __init__(self, templatePath="cg-tpl", indentSpace=" " * 3, verbose=CGKIT_VERBOSITY):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseGraph]")
        self.templatePath = Path(templatePath)
        self._stree = SourceTree(self.templatePath, indentSpace, verbose=verbose, verbosePre="!", verbosePost="")
        self._linkStack = list()
        self._pathStack = dict()
        self._taskfn_id = 0
        self._callReturnStack = list()

    def __call__(self, graph, graphAttribute):
        if self.verbose:
            print(self.verbose_prefix, f"Parsing graph at level={graph.level}")
        if not graph.isSubgraph():
            # parse the top-level graph
            if self.verbose:
                print(self.verbose_prefix, "Parse top-level graph")
            self._stree.initTree(graph.tpl)
            linkKeyList = srctree.search_links(self._stree.getTree())
            self.pushLinks(linkKeyList)
            self.pushSourceTreePath(self._stree.getLastLinkPath(linkKeyList))
            self._callReturnStack.append(CtrRet.SUCCESS)
        else:  # otherwise graph is a subgraph
            if self.verbose:
                print(self.verbose_prefix, "Parse subgraph, do nothing")

            tree_subGraph = srctree.load(INTERNAL_TEMPLATE_PATH / "cg-tpl.subGraph.json")
            tree_subGraph["_param:level"] = str(graph.level)
            tree_subGraph["_param:args"] = ", ".join(graphAttribute["args"])
            ctrret, pathInfo = _insertConnectors(self, tree_subGraph, self.verbose, self.verbose_prefix)
            self._callReturnStack.append(ctrret)
            if CtrRet.SUCCESS == ctrret:
                linkKeyList = srctree.search_links(tree_subGraph)
                self.pushLinks(linkKeyList)
                self.pushSourceTreePath(self._stree.getLastLinkPath(linkKeyList))
        return self._callReturnStack[-1]

    def q(self, graph, graphAttribute):
        assert self._callReturnStack
        if CtrRet.SUCCESS == self._callReturnStack.pop():
            if self.verbose:
                print(self.verbose_prefix, f"Terminate parsing graph at level={graph.level}")
            linkKeyList = self.popLinks()
            self.popSourceTreePath(linkKeyList)
            assert graph.isSubgraph() or 0 == sum([len(p) for p in self._pathStack.values()])
            return CtrRet.SUCCESS
        else:
            return CtrRet.ERROR

    def pushLinks(self, linkKeyList):
        assert isinstance(linkKeyList, list), type(linkKeyList)
        return self._linkStack.append(linkKeyList)

    def popLinks(self):
        return self._linkStack.pop()

    def pushSourceTreePath(self, linkKeyPath):
        assert isinstance(linkKeyPath, dict), type(linkKeyPath)
        if self.verbose:
            print(self.verbose_prefix, "Push path to stack (before):", self._pathStack)
        for key, path in linkKeyPath.items():
            if key in self._pathStack:
                self._pathStack[key].append(path)
            else:
                self._pathStack[key] = [path]
        if self.verbose:
            print(self.verbose_prefix, "Push path to stack (after): ", self._pathStack)
        return

    def popSourceTreePath(self, linkKey):
        if self.verbose:
            print(self.verbose_prefix, "Pop path from stack (before):", self._pathStack)
        try:
            for key in linkKey:
                assert self._pathStack[key], "Path stack should not be empty"
                self._pathStack[key].pop()
        except KeyError:
            assert self._pathStack[linkKey], "Path stack should not be empty"
            self._pathStack[linkKey].pop()
        except:
            raise
        if self.verbose:
            print(self.verbose_prefix, "Pop path from stack (after): ", self._pathStack)
        return

    def getSourceTree(self):
        return self._stree

    def getSourceTreePath(self, linkKey):
        return self._pathStack[linkKey][-1]


class Ctr_ParseNode(AbstractControllerNode):
    def __init__(self, ctrParseGraph, workTemplate="cg-tpl.work.json", verbose=CGKIT_VERBOSITY):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseNode]")
        self._ctrParseGraph = ctrParseGraph
        self._templatePath = ctrParseGraph.templatePath
        self._tree_work = srctree.load(INTERNAL_TEMPLATE_PATH / workTemplate)
        self._beginEnd_callReturnStack = dict()

    def __call__(self, graph, node, nodeAttribute):
        assert "obj" in nodeAttribute, nodeAttribute.keys()
        if isinstance(nodeAttribute["obj"], WorkNode):
            return self._call_WorkNode(nodeAttribute["obj"], graph, node, nodeAttribute)
        elif isinstance(nodeAttribute["obj"], SetupNode):
            return self._call_SetupNode(nodeAttribute["obj"], graph, node, nodeAttribute)
        elif isinstance(nodeAttribute["obj"], GenericBeginNode):
            return self._call_GenericBeginNode(nodeAttribute["obj"], graph, node, nodeAttribute)
        elif isinstance(nodeAttribute["obj"], GenericEndNode):
            return self._call_GenericEndNode(nodeAttribute["obj"], graph, node, nodeAttribute)
        else:
            if self.verbose:
                print(self.verbose_prefix, f"Nothing to parse for node object {type(nodeAttribute['obj'])}")
            return CtrRet.VOID

    def _call_WorkNode(self, workNode, graph, node, nodeAttribute):
        assert isinstance(workNode, WorkNode), type(workNode)
        tree_work = self._tree_work
        assert tree_work is not None
        # set function name
        fnName = getattr(workNode, "name")
        # set function arguments
        fnArgs = getattr(workNode, "args")
        fnArgs = ", ".join(fnArgs)
        # set (local) source tree parameters
        if self.verbose:
            print(self.verbose_prefix, f"Parse code of node type={workNode.type}, fnName={fnName}, fnArgs=({fnArgs})")
        tree_work["_param:functionName"] = fnName
        tree_work["_param:functionArgs"] = fnArgs
        # enclosing execute connector
        tree_work = _encloseConnector(tree_work, workNode.startswith, workNode.endswith)
        # insert code into source tree
        ctrret, pathInfo = _insertConnectors(self._ctrParseGraph, tree_work, self.verbose, self.verbose_prefix)
        return ctrret

    def _call_GenericBeginNode(self, beginNode, graph, node, nodeAttribute):
        assert isinstance(beginNode, GenericBeginNode), type(beginNode)
        assert 1 == nodeAttribute["obj"].nEndNodes()  # TODO can be made more general for multiple end nodes
        if self.verbose:
            print(self.verbose_prefix, f"Parse code of node type={beginNode.type}, name={beginNode.name}")
        tree_begin = srctree.load(self._templatePath / beginNode.tpl)
        assert 0 < len(srctree.search_connectors(tree_begin))
        tree_begin = _encloseConnector(tree_begin, beginNode.startswith, beginNode.endswith)
        ctrret, pathInfo = _insertConnectors(self._ctrParseGraph, tree_begin, self.verbose, self.verbose_prefix)
        returnStackKey = beginNode.name
        i = 0
        while returnStackKey in self._beginEnd_callReturnStack.keys():
            i += 1
            returnStackKey = f"{beginNode.name}_{i}"
        # save return stack key for processing correcponding endNode
        beginNode.returnStackKey = returnStackKey

        self._beginEnd_callReturnStack[returnStackKey] = list()
        callReturnStack = self._beginEnd_callReturnStack[returnStackKey]

        callReturnStack.append(ctrret)
        if CtrRet.SUCCESS == ctrret:
            stree = self._ctrParseGraph.getSourceTree()
            linkKeyList = srctree.search_links(tree_begin)
            self._ctrParseGraph.pushLinks(linkKeyList)
            self._ctrParseGraph.pushSourceTreePath(stree.getLastLinkPath(linkKeyList))
        return ctrret

    def _call_GenericEndNode(self, endNode, graph, node, nodeAttribute):
        assert isinstance(endNode, GenericEndNode), type(endNode)
        assert endNode.name == endNode.beginNode.name
        # TODO check if all end nodes were visited
        if self.verbose:
            print(self.verbose_prefix, f"Parse code of node type={endNode.type}, name={endNode.name}")
        # process as generic end node
        returnStackKey = endNode.beginNode.returnStackKey
        callReturnStack = self._beginEnd_callReturnStack[returnStackKey]
        assert isinstance(callReturnStack, list)
        if CtrRet.SUCCESS == callReturnStack.pop():
            linkKeyList = self._ctrParseGraph.popLinks()
            self._ctrParseGraph.popSourceTreePath(linkKeyList)
            return CtrRet.SUCCESS
        return CtrRet.ERROR

    def _call_SetupNode(self, setupNode, graph, node, nodeAttribute):
        assert isinstance(setupNode, SetupNode), type(setupNode)
        # setup parsing
        tree = srctree.load(self._templatePath / setupNode.tpl)
        if self.verbose:
            print(self.verbose_prefix, f"Parse code of node type={setupNode.type}, name={setupNode.name}")
        # insert code into source tree
        tree = _encloseConnector(tree, setupNode.startswith, setupNode.endswith)
        ctrret, pathInfo = _insertConnectors(self._ctrParseGraph, tree, self.verbose, self.verbose_prefix)
        return ctrret


class Ctr_ParseMultiEdge(AbstractControllerMultiEdge):
    def __init__(self, ctrParseGraph, templatePath="cg-tpl", verbose=CGKIT_VERBOSITY):
        super().__init__(controllerType="view", verbose=verbose, verbose_prefix="[Ctr_ParseMultiEdge]")
        self._ctrParseGraph = ctrParseGraph
        self._templatePath = ctrParseGraph.templatePath
        self._callReturnStack = list()

    def __call__(self, graph, node, nodeAttribute, successors):
        tree_concurrent = srctree.load(INTERNAL_TEMPLATE_PATH / "cg-tpl.concurrent_work.json")
        # parse code into source tree
        if self.verbose:
            print(self.verbose_prefix, f"Parse code of node = {node}")
        ctrret, pathInfo = _insertConnectors(self._ctrParseGraph, tree_concurrent, self.verbose, self.verbose_prefix)
        self._callReturnStack.append(ctrret)
        if CtrRet.SUCCESS == ctrret:
            stree = self._ctrParseGraph.getSourceTree()
            linkKeyList = srctree.search_links(tree_concurrent)
            self._ctrParseGraph.pushLinks(linkKeyList)
            self._ctrParseGraph.pushSourceTreePath(stree.getLastLinkPath(linkKeyList))
        return ctrret

    def q(self, graph, node, nodeAttribute, predecessors):
        assert self._callReturnStack
        if self.verbose:
            print(self.verbose_prefix, 'Exit MultiEdge')
        if CtrRet.SUCCESS == self._callReturnStack.pop():
            linkKeyList = self._ctrParseGraph.popLinks()
            self._ctrParseGraph.popSourceTreePath(linkKeyList)
            return CtrRet.SUCCESS
        else:
            return CtrRet.ERROR

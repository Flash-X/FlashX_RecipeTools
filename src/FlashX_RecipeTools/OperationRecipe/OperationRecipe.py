from cgkit.cflow.graph import ControlFlowGraph

from ._controllers import (
    Ctr_initRecipeNode,
    Ctr_ParseGraph,
    Ctr_ParseNode,
    Ctr_ParseMultiEdge,
)
from ..constants import VERBOSE_DEFAULT, KEEP_KEY


class OperationRecipe(ControlFlowGraph):
    def __init__(self, tpl=None, verbose=VERBOSE_DEFAULT, **kwargs):
        super().__init__(verbose=verbose, **kwargs)

        self.tpl = tpl

        self.__init_node = Ctr_initRecipeNode()
        self.__is_empty = True

    def _shallowCopy(self):
        shallowCopy = super()._shallowCopy()
        shallowCopy.tpl = self.tpl
        return shallowCopy

    def add_item(self, node, after):
        handle = self.linkNode(node, controllerNode=self.__init_node)(after)

        if self.__is_empty:
            self.setEdgeAttribute((self.root, handle), KEEP_KEY, True)
            self.__is_empty = False

        return handle

    def parse_operation_codes(self, name:str, templatePath:str):
        ctrParseGraph = Ctr_ParseGraph(templatePath=templatePath, verbose=self.verbose)
        ctrParseNode = Ctr_ParseNode(ctrParseGraph, verbose=self.verbose)
        ctrParseMultiEdge = Ctr_ParseMultiEdge(ctrParseGraph, verbose=self.verbose)
        self.parseCode(
            controllerGraph=ctrParseGraph,
            controllerNode=ctrParseNode,
            controllerMultiEdge=ctrParseMultiEdge,
        )

        # parse source tree
        stree = ctrParseGraph.getSourceTree()
        if self.verbose:
            stree.dump(f"{name}.json")
        with open(f"{name}.F90-mc", "w") as f:
            f.write(stree.parse())



from cgkit.cflow.graph import ControlFlowGraph

from .recipe_controllers import Ctr_initRecipeNode
from .nodes import genericBeginNode, genericEndNode
from .constants import VERBOSE_DEFAULT, DEVICE_KEY, KEEP_KEY


def ConstructBeginEndNodes(name, tpl):
    beginNode = genericBeginNode(name, tpl)
    endNode = genericEndNode(name, beginNode)
    beginNode.appendEndNode(endNode)

    return beginNode, endNode


class Recipe(ControlFlowGraph):
    def __init__(self, tpl=None, verbose=VERBOSE_DEFAULT, **kwargs):
        super().__init__(verbose=verbose, **kwargs)

        self.tpl = tpl

        self.__init_node = Ctr_initRecipeNode()
        self.__is_empty = True

    def add_item(self, node, invoke_after, map_to=None):
        handle = self.linkNode(node, controllerNode=self.__init_node)(invoke_after)
        if map_to is None:
            # TODO: This should be host and we presently assume that all block
            # iterations start and end on the host.
            # TODO: It doesn't seem right that the recipe class has to put all
            # device keys to lower.  Rather, the lower level code should be
            # case-insensitive.
            self.setNodeAttribute(handle, DEVICE_KEY, None)
        else:
            self.setNodeAttribute(handle, DEVICE_KEY, map_to.lower())

        if self.__is_empty:
            self.setEdgeAttribute((self.root, handle), KEEP_KEY, True)
            self.__is_empty = False

        return handle

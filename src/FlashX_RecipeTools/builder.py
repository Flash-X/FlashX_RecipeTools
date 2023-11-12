from cgkit.cflow.graph import ControlFlowGraph

from .controllers import Ctr_initRecipeNode
from .nodes import (
    genericBeginNode,
    genericEndNode,
    TileIteratorBeginNode,
    TileIteratorEndNode,
)
from .constants import VERBOSE_DEFAULT, DEVICE_KEY, KEEP_KEY


def ConstructBeginEndNodes(name, tpl, startswith="", endswith=""):
    beginNode = genericBeginNode(name, tpl, startswith=startswith, endswith=endswith)
    endNode = genericEndNode(name, beginNode)
    beginNode.appendEndNode(endNode)

    return beginNode, endNode


def ConstructTileLoop(itorVar="itor", itorType="LEAF", **kwargs):
    beginNode = TileIteratorBeginNode(itorVar, itorType, **kwargs)
    endNode = TileIteratorEndNode(beginNode)
    beginNode.appendEndNode(endNode)

    return beginNode, endNode


class Recipe(ControlFlowGraph):
    def __init__(self, tpl=None, verbose=VERBOSE_DEFAULT, **kwargs):
        super().__init__(verbose=verbose, **kwargs)

        self.tpl = tpl
        self.opspecs = dict()
        self.opspec_fnames = dict()

        self.__init_node = Ctr_initRecipeNode()
        self.__is_empty = True

    def _shallowCopy(self):
        shallowCopy = super()._shallowCopy()
        shallowCopy.tpl = self.tpl
        shallowCopy.opspecs = self.opspecs.copy()
        shallowCopy.opspec_fnames = self.opspec_fnames.copy()
        return shallowCopy

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

    def add_operation_spec(self, opspec:dict):
        assert len(opspec) != 0
        opspec_name = opspec["name"]
        self.opspecs.update({opspec_name: opspec})
        self.opspec_fnames.update({opspec_name: opspec["fname"]})

    def get_operation_spec(self, operation_name:str):
        assert operation_name in self.opspecs.keys(), (
            f"{operation_name} spec is not found in the given recipe"
        )
        return self.opspecs[operation_name]

    def get_operation_spec_fname(self, operation_name:str):
        assert operation_name in self.opspec_fnames.keys(), (
            f"{operation_name} spec is not found in the given recipe"
        )
        return self.opspec_fnames[operation_name]

from .TimeStepRecipe import TimeStepRecipe
from ._controller import (
    Ctr_InitNodeFromOpspec,
    Ctr_SetupEdge,
    Ctr_MarkEdgeAsKeep,
    Ctr_InitSubgraph,
    Ctr_ParseTFGraph,
    Ctr_ParseTFNode,
    Ctr_ParseTFMultiEdge,
)


def compile_recipe(recipe: TimeStepRecipe):
    # gather argument list of each nodes
    recipe.traverse(controllerNode=Ctr_InitNodeFromOpspec())

    # transform into hierarchical graph
    recipe.traverse(controllerEdge=Ctr_SetupEdge())
    h = recipe.extractHierarchicalGraph(
        controllerMarkEdge=Ctr_MarkEdgeAsKeep(),
        controllerInitSubgraph=Ctr_InitSubgraph()
    )

    # generate intermediate TF data
    ctrParseTFGraph = Ctr_ParseTFGraph()
    ctrParseTFNode = Ctr_ParseTFNode(ctrParseTFGraph)
    ctrParseTFMultiedge = Ctr_ParseTFMultiEdge(ctrParseTFGraph)
    h.traverseHierarchy(
        controllerGraph=ctrParseTFGraph,
        controllerNode=ctrParseTFNode,
        controllerMultiEdge=ctrParseTFMultiedge
    )

    return list(ctrParseTFGraph.getTFData())

#!/usr/bin/env python

import FlashX_RecipeTools as fr

from matplotlib import pyplot as plt

PP = {
    "NDIM": 2,
    "NXB": 16,
    "NYB": 16,
    "NZB": 1,
    "NGUARD": 4,
    "K1D": 1,
    "K2D": 1,
    "K3D": 0,
    "NFLUXES": 5,
    "DENS_VAR": 1,
    "PRES_VAR": 2,
    "VELX_VAR": 3,
    "VELY_VAR": 4,
    "VELZ_VAR": 5,
    "ENER_VAR": 6,
    "EINT_VAR": 7,
    "TEMP_VAR": 8,
    "GAMC_VAR": 9,
}


def simpleUnsplit(recipe, root):
    from _nodes import simpleUnsplit_nodes

    n = simpleUnsplit_nodes()

    _tileBegin = recipe.add_item(n.tileBegin, invoke_after=root, map_to="cpu")

    _soundSpd = recipe.add_item(n.soundSpd, invoke_after=_tileBegin, map_to="gpu")
    _flx = recipe.add_item(n.flx, invoke_after=_soundSpd, map_to="gpu")
    _fly = recipe.add_item(n.fly, invoke_after=_soundSpd, map_to="gpu")
    _flz = recipe.add_item(n.flz, invoke_after=_soundSpd, map_to="gpu")
    _updSoln = recipe.add_item(n.updSoln, invoke_after=[_flx, _fly, _flz], map_to="gpu")

    _doEos = recipe.add_item(n.doEos, invoke_after=_updSoln, map_to="cpu")

    _tileEnd = recipe.add_item(n.tileEnd, invoke_after=_doEos, map_to="cpu")

    return _tileEnd


def main():
    # gather operation spec
    op_spec = fr.opspec.load("Hydro_op1.json", PP)
    # create empty recipe
    recipe = fr.Recipe(tpl="cg-tpl.Hydro.F90", operation_spec=op_spec)

    # build recipe
    _endNode = simpleUnsplit(recipe, recipe.root)
    _endNode = recipe.add_item(fr.LeafNode(), invoke_after=_endNode)
    recipe.verbose = True

    # gather argument list of each nodes
    recipe.traverse(controllerNode=fr.opspec.Ctr_InitNodeFromOpspec(verbose=False))


    print("+++++++++++++++++++++++++++++++++")

    # transform into hierarchical graph
    recipe.traverse(controllerEdge=fr.Ctr_SetupEdge(verbose=False))
    h = recipe.extractHierarchicalGraph(controllerMarkEdge=fr.Ctr_MarkEdgeAsKeep(verbose=False),
                                        controllerInitSubgraph=fr.Ctr_InitSubgraph(verbose=False))
    h.verbose = False

    # parse code from hierarchical graph
    ctrParseGraph = fr.Ctr_ParseGraph(templatePath="cg-tpl", verbose=False)
    ctrParseNode = fr.Ctr_ParseNode(ctrParseGraph, verbose=False)
    ctrParseMultiEdge = fr.Ctr_ParseMultiEdge(ctrParseGraph, verbose=False)
    h.parseCode(
        controllerGraph=ctrParseGraph,
        controllerNode=ctrParseNode,
        controllerMultiEdge=ctrParseMultiEdge,
    )


    # generate TF spec
    ctrParseTFGraph = fr.opspec.Ctr_ParseTFGraph()
    ctrParseTFNode = fr.opspec.Ctr_ParseTFNode(ctrParseTFGraph)
    ctrParseTFMultiedge = fr.opspec.Ctr_ParseTFMultiEdge(ctrParseTFGraph)
    h.traverseHierarchy(controllerGraph=ctrParseTFGraph,
                        controllerNode=ctrParseTFNode,
                        controllerMultiEdge=ctrParseTFMultiedge)

    ctrParseTFGraph.dumpTFspecs(indent=2)

    # parse operation spec for debugging
    fr.opspec.dump(op_spec, "__Hydro_op1_pped.json", indent=2)

    # parse source tree
    stree = ctrParseGraph.getSourceTree()
    stree.dump("__tree.json")
    with open("__Hydro.F90-mc", "w") as f:
        f.write(stree.parse())

    # plot
    # set constants
    PLOTID_GRAPH = 211
    PLOTID_H_GRAPH = 212

    plt.tight_layout()
    fig = plt.figure(figsize=(10, 8))

    ax = plt.subplot(PLOTID_GRAPH)
    ax.set_title("Control Flow Graph")
    recipe.plot(nodeLabels=False, edgeLabels=True)

    ax = plt.subplot(PLOTID_H_GRAPH)
    ax.set_title("Coarse Control Flow Graph")
    h.plot(nodeLabels=True, edgeLabels=True)

    # plt.show()

    fig.savefig("__graphs.pdf")


if __name__ == "__main__":
    main()

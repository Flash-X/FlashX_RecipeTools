#!/usr/bin/env python

import FlashX_RecipeTools as fr

from matplotlib import pyplot as plt


def simpleUnsplit(recipe, root):
    from _nodes import simpleUnsplit_nodes

    n = simpleUnsplit_nodes()

    _tileBegin = recipe.add_item(n.tileBegin, invoke_after=root, map_to="cpu")

    _soundSpd = recipe.add_item(n.soundSpd, invoke_after=_tileBegin, map_to="cpu")
    _flx = recipe.add_item(n.flx, invoke_after=_soundSpd, map_to="cpu")
    _fly = recipe.add_item(n.fly, invoke_after=_soundSpd, map_to="cpu")
    _tst = recipe.add_item(n.tst, invoke_after=_fly, map_to="cpu")
    _flz = recipe.add_item(n.flz, invoke_after=_soundSpd, map_to="cpu")
    _updSoln = recipe.add_item(n.updSoln, invoke_after=[_flx, _tst, _flz], map_to="cpu")

    _doEos = recipe.add_item(n.doEos, invoke_after=_updSoln, map_to="cpu")

    _tileEnd = recipe.add_item(n.tileEnd, invoke_after=_doEos, map_to="cpu")

    return recipe


def main():
    # create empty recipe
    recipe = fr.Recipe(tpl="cg-tpl.Hydro.F90")

    recipe = simpleUnsplit(recipe, recipe.root)

    recipe.verbose=True

    # transform into hierarchical graph
    recipe.traverse(controllerEdge=fr.Ctr_SetupEdge())
    h = recipe.extractHierarchicalGraph(controllerMarkEdge=fr.Ctr_MarkEdgeAsKeep(verbose=False),
                                        controllerInitSubgraph=fr.Ctr_InitSubgraph(verbose=False))
    h.tpl = "cg-tpl.Hydro.F90"

    h = recipe
    h.verbose = True

    # parse code from hierarchical graph
    ctrParseGraph = fr.Ctr_ParseGraph(templatePath="cg-tpl", verbose=False)
    ctrParseNode = fr.Ctr_ParseNode(ctrParseGraph, verbose=False)
    ctrParseMultiEdge = fr.Ctr_ParseMultiEdge(ctrParseGraph, verbose=False)
    h.parseCode(
        controllerGraph=ctrParseGraph,
        controllerNode=ctrParseNode,
        controllerMultiEdge=ctrParseMultiEdge,
    )

    # parse source tree
    stree = ctrParseGraph.getSourceTree()
    stree.dump("__tree.json")
    with open("__Hydro.F90-mc", "w") as f:
        f.write(stree.parse())

    # plot
    # set constants
    PLOTID_GRAPH = 111
    PLOTID_H_GRAPH = 212

    plt.tight_layout()
    fig = plt.figure(figsize=(10, 4))

    ax = plt.subplot(PLOTID_GRAPH)
    ax.set_title("Control Flow Graph")
    recipe.plot(nodeLabels=False)

    # ax = plt.subplot(PLOTID_H_GRAPH)
    # ax.set_title("Coarse Control Flow Graph")
    # h.plot(nodeLabels=True)

    # plt.show()

    fig.savefig("__graphs.pdf")


if __name__ == "__main__":
    main()

#!/usr/bin/env python

import FlashX_RecipeTools as fr

from matplotlib import pyplot as plt
from argparse import ArgumentParser


def amrex_tele(recipe, root):
    from _spark_nodes import spark_amrex_tele_nodes

    n = spark_amrex_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, invoke_after=root)
    # levels
    _levelBegin = recipe.add_item(n.levelBegin, invoke_after=_fillGC)
    _commFluxes = recipe.add_item(n.commFluxes, invoke_after=_levelBegin)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, invoke_after=_commFluxes)
    _shockDet = recipe.add_item(n.shockDet, invoke_after=_blockBegin)
    _initSoln = recipe.add_item(n.initSoln, invoke_after=_blockBegin)
    _permLims = recipe.add_item(n.permLims, invoke_after=_blockBegin)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, invoke_after=_initSoln)

    _gravAccel = recipe.add_item(n.gravAccel, invoke_after=_stageBegin)
    _calcLims = recipe.add_item(n.calcLims, invoke_after=_gravAccel)
    _getFlat = recipe.add_item(n.getFlat, invoke_after=_calcLims)
    _getFlux = recipe.add_item(n.getFlux, invoke_after=_getFlat)
    _saveFluxBuf = recipe.add_item(n.saveFluxBuf, invoke_after=_getFlux)
    _updSoln = recipe.add_item(n.updSoln, invoke_after=_getFlux)
    _reAbund = recipe.add_item(n.reAbund, invoke_after=_updSoln)
    _doEos = recipe.add_item(n.doEos, invoke_after=_reAbund)

    _stageEnd = recipe.add_item(n.stageEnd, invoke_after=_doEos)
    # end stages

    _ifLevGToneBegin = recipe.add_item(n.ifLevGToneBegin, invoke_after=_stageEnd)
    _putFlux = recipe.add_item(n.putFlux, invoke_after=_ifLevGToneBegin)
    _ifLevGToneEnd = recipe.add_item(n.ifLevGToneEnd, invoke_after=_putFlux)

    _ifLevLTmaxBegin = recipe.add_item(n.ifLevLTmaxBegin, invoke_after=_ifLevGToneEnd)
    _getFluxCorr_xtra = recipe.add_item(n.getFluxCorr_xtra, invoke_after=_ifLevLTmaxBegin)
    _corrSoln = recipe.add_item(n.corrSoln, invoke_after=_getFluxCorr_xtra)
    _ifLevLTmaxEnd = recipe.add_item(n.ifLevLTmaxEnd, invoke_after=_corrSoln)

    _blockEnd = recipe.add_item(n.blockEnd, invoke_after=_ifLevLTmaxEnd)
    # end blocks

    _levelEnd_id = recipe.add_item(n.levelEnd, invoke_after=_blockEnd)
    # end levels

    return recipe


def pm_tele(recipe, root):
    from _spark_nodes import spark_paramesh_tele_nodes

    n = spark_paramesh_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, invoke_after=root)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, invoke_after=_fillGC)
    _shockDet = recipe.add_item(n.shockDet, invoke_after=_blockBegin)
    _initSoln = recipe.add_item(n.initSoln, invoke_after=_blockBegin)
    _permLims = recipe.add_item(n.permLims, invoke_after=_blockBegin)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, invoke_after=_initSoln)

    _gravAccel = recipe.add_item(n.gravAccel, invoke_after=_stageBegin)
    _calcLims = recipe.add_item(n.calcLims, invoke_after=_gravAccel)
    _getFlat = recipe.add_item(n.getFlat, invoke_after=_calcLims)
    _getFlux = recipe.add_item(n.getFlux, invoke_after=_getFlat)
    _saveFluxBuf = recipe.add_item(n.saveFluxBuf, invoke_after=_getFlux)
    _updSoln = recipe.add_item(n.updSoln, invoke_after=_getFlux)
    _reAbund = recipe.add_item(n.reAbund, invoke_after=_updSoln)
    _doEos = recipe.add_item(n.doEos, invoke_after=_reAbund)

    _stageEnd = recipe.add_item(n.stageEnd, invoke_after=_doEos)
    # end stages

    _putFlux = recipe.add_item(n.putFlux, invoke_after=_stageEnd)

    _blockEnd = recipe.add_item(n.blockEnd, invoke_after=_putFlux)
    # end blocks

    # TODO: missing if(hy_fluxCorrect) here
    _commFluxes = recipe.add_item(n.commFluxes, invoke_after=_blockEnd)
    # second blocks
    _blockBegin2 = recipe.add_item(n.blockBegin2, invoke_after=_commFluxes)
    _getFluxCorr_block = recipe.add_item(n.getFluxCorr_block, invoke_after=_blockBegin2)
    _corrSoln = recipe.add_item(n.corrSoln, invoke_after=_getFluxCorr_block)
    _blockEnd2 = recipe.add_item(n.blockEnd2, invoke_after=_corrSoln)
    # end second blocks

    return recipe


def main(variant):
    # create empty recipe
    recipe = fr.Recipe(tpl="cg-tpl.Hydro.F90")

    if variant == "amrex_tele":
        recipe = amrex_tele(recipe, recipe.root)
    elif variant == "pm_tele":
        recipe = pm_tele(recipe, recipe.root)
    else:
        raise ValueError("invalid variant")

    # TODO:
    # transform into hierarchical graph
    # recipe.traverse(controllerEdge=fr.Ctr_SetupEdge())
    # h = recipe.extractHierarchicalGraph(controllerMarkEdge=fr.Ctr_MarkEdgeAsKeep(),
    #                                     controllerInitSubgraph=fr.Ctr_InitSubgraph())
    h = recipe

    # parse code from hierarchical graph
    ctrParseGraph = fr.Ctr_ParseGraph(templatePath="cg-tpl")
    ctrParseNode = fr.Ctr_ParseNode(ctrParseGraph)
    ctrParseMultiEdge = fr.Ctr_ParseMultiEdge(ctrParseGraph)
    h.parseCode(
        controllerGraph=ctrParseGraph,
        controllerNode=ctrParseNode,
        controllerMultiEdge=ctrParseMultiEdge,
    )

    # parse source tree
    stree = ctrParseGraph.getSourceTree()
    stree.dump(f"__tree_{variant}.json")
    with open(f"__Hydro_{variant}.F90-mc", "w") as f:
        f.write(stree.parse())

    # plot
    # set constants
    PLOTID_GRAPH = 211
    PLOTID_H_GRAPH = 212

    fig = plt.figure(figsize=(16, 8))

    ax = plt.subplot(PLOTID_GRAPH)
    ax.set_title("Control Flow Graph")
    recipe.plot(nodeLabels=True)

    ax = plt.subplot(PLOTID_H_GRAPH)
    ax.set_title("Coarse Control Flow Graph")
    h.plot(nodeLabels=True)

    # plt.show()

    fig.savefig(f"__graphs_{variant}.pdf")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("variant", type=str, choices=["amrex_tele", "pm_tele"])
    args = parser.parse_args()

    main(args.variant)

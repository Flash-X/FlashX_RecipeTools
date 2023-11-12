#!/usr/bin/env python

import FlashX_RecipeTools as fr

from matplotlib import pyplot as plt
from argparse import ArgumentParser


def _spark_stage_init(recipe, root, n):
    _shockDet = recipe.add_item(n.shockDet, invoke_after=root)
    _initSoln = recipe.add_item(n.initSoln, invoke_after=root)
    _permLims = recipe.add_item(n.permLims, invoke_after=root)

    # leaf node does nothing
    leaf = fr.LeafNode()
    _leaf = recipe.add_item(leaf, invoke_after=[_shockDet, _initSoln, _permLims])

    return _leaf


def _spark_stage(recipe, root, n):
    _gravAccel = recipe.add_item(n.gravAccel, invoke_after=root)
    _calcLims = recipe.add_item(n.calcLims, invoke_after=root)
    _getFlat = recipe.add_item(n.getFlat, invoke_after=_calcLims)
    _getFlux = recipe.add_item(n.getFlux, invoke_after=_getFlat)
    _saveFluxBuf = recipe.add_item(n.saveFluxBuf, invoke_after=_getFlux)
    _updSoln = recipe.add_item(n.updSoln, invoke_after=_getFlux)
    _reAbund = recipe.add_item(n.reAbund, invoke_after=_updSoln)
    _doEos = recipe.add_item(n.doEos, invoke_after=_reAbund)

    return _doEos


def amrex_tele(recipe, root):
    from _spark_nodes import spark_amrex_tele_nodes

    n = spark_amrex_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, invoke_after=root)
    # levels
    _levelBegin = recipe.add_item(n.levelBegin, invoke_after=_fillGC)
    _commFluxes = recipe.add_item(n.commFluxes, invoke_after=_levelBegin)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, invoke_after=_commFluxes)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, invoke_after=_stageInit)
    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageBegin, n)
    # end stages
    _stageEnd = recipe.add_item(n.stageEnd, invoke_after=_innerStage)

    _ifLevGToneBegin = recipe.add_item(n.ifLevGToneBegin, invoke_after=_stageEnd)
    _putFlux = recipe.add_item(n.putFlux, invoke_after=_ifLevGToneBegin)
    _ifLevGToneEnd = recipe.add_item(n.ifLevGToneEnd, invoke_after=_putFlux)

    _ifLevLTmaxBegin = recipe.add_item(n.ifLevLTmaxBegin, invoke_after=_ifLevGToneEnd)
    _getFluxCorr_xtra = recipe.add_item(n.getFluxCorr_xtra, invoke_after=_ifLevLTmaxBegin)
    _corrSoln = recipe.add_item(n.corrSoln, invoke_after=_getFluxCorr_xtra)
    _ifLevLTmaxEnd = recipe.add_item(n.ifLevLTmaxEnd, invoke_after=_corrSoln)

    _blockEnd = recipe.add_item(n.blockEnd, invoke_after=_ifLevLTmaxEnd)
    # end blocks

    _levelEnd = recipe.add_item(n.levelEnd, invoke_after=_blockEnd)
    # end levels

    return recipe


def pm_tele(recipe, root):
    from _spark_nodes import spark_paramesh_tele_nodes

    n = spark_paramesh_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, invoke_after=root)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, invoke_after=_fillGC)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, invoke_after=_stageInit)
    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageBegin, n)
    # end stages
    _stageEnd = recipe.add_item(n.stageEnd, invoke_after=_innerStage)

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


def pm_nontele(recipe, root):
    from _spark_nodes import spark_paramesh_nontele_nodes

    n = spark_paramesh_nontele_nodes()

    _stageBegin = recipe.add_item(n.stageBegin, invoke_after=root)
    _fillGC = recipe.add_item(n.fillGC, invoke_after=_stageBegin)
    _blockBegin = recipe.add_item(n.blockBegin, invoke_after=_fillGC)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageInit, n)

    _putFlux = recipe.add_item(n.putFlux, invoke_after=_innerStage)
    _saveSoln = recipe.add_item(n.saveSoln, invoke_after=_innerStage)

    _blockEnd = recipe.add_item(n.blockEnd, invoke_after=_saveSoln)
    _stageEnd = recipe.add_item(n.stageEnd, invoke_after=_blockEnd)


    # TODO: missing if(hy_fluxCorrect) here
    _commFluxes = recipe.add_item(n.commFluxes, invoke_after=_stageEnd)
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
    elif variant == "pm_nontele":
        recipe = pm_nontele(recipe, recipe.root)
    else:
        raise ValueError("invalid variant")

    # TODO:
    # transform into hierarchical graph
    # recipe.traverse(controllerEdge=fr.Ctr_SetupEdge())
    # h = recipe.extractHierarchicalGraph(controllerMarkEdge=fr.Ctr_MarkEdgeAsKeep(),
    #                                     controllerInitSubgraph=fr.Ctr_InitSubgraph())
    h = recipe

    h.verbose = True

    # parse code from hierarchical graph
    ctrParseGraph = fr.Ctr_ParseGraph(templatePath="cg-tpl", verbose=False)
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
    PLOTID_GRAPH = 111

    fig = plt.figure(figsize=(16, 6))

    ax = plt.subplot(PLOTID_GRAPH)
    ax.set_title("Control Flow Graph")
    h.plot(nodeLabels=True)

    # plt.show()

    fig.savefig(f"__graphs_{variant}.pdf")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("variant", type=str, choices=["amrex_tele", "pm_tele", "pm_nontele"])
    args = parser.parse_args()

    main(args.variant)

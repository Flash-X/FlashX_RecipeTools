#!/usr/bin/env python

import FlashX_RecipeTools as flashx

from matplotlib import pyplot as plt
from argparse import ArgumentParser


def _spark_stage_init(recipe, root, n):
    _shockDet = recipe.add_item(n.shockDet, after=root)
    _initSoln = recipe.add_item(n.initSoln, after=root)
    _permLims = recipe.add_item(n.permLims, after=root)

    # leaf node does nothing
    leaf = flashx.nodes.LeafNode()
    _leaf = recipe.add_item(leaf, after=[_shockDet, _initSoln, _permLims])

    return _leaf


def _spark_stage(recipe, root, n):
    _gravAccel = recipe.add_item(n.gravAccel, after=root)
    _calcLims = recipe.add_item(n.calcLims, after=root)
    _getFlat = recipe.add_item(n.getFlat, after=_calcLims)
    _getFlux = recipe.add_item(n.getFlux, after=_getFlat)
    _saveFluxBuf = recipe.add_item(n.saveFluxBuf, after=_getFlux)
    _updSoln = recipe.add_item(n.updSoln, after=_getFlux)
    _reAbund = recipe.add_item(n.reAbund, after=_updSoln)
    _doEos = recipe.add_item(n.doEos, after=_reAbund)

    return _doEos


def amrex_tele(recipe, root):
    from _spark_nodes import spark_amrex_tele_nodes

    n = spark_amrex_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, after=root)
    # levels
    _levelBegin = recipe.add_item(n.levelBegin, after=_fillGC)
    _commFluxes = recipe.add_item(n.commFluxes, after=_levelBegin)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, after=_commFluxes)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, after=_stageInit)
    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageBegin, n)
    # end stages
    _stageEnd = recipe.add_item(n.stageEnd, after=_innerStage)

    _ifLevGToneBegin = recipe.add_item(n.ifLevGToneBegin, after=_stageEnd)
    _putFlux = recipe.add_item(n.putFlux, after=_ifLevGToneBegin)
    _ifLevGToneEnd = recipe.add_item(n.ifLevGToneEnd, after=_putFlux)

    _ifLevLTmaxBegin = recipe.add_item(n.ifLevLTmaxBegin, after=_ifLevGToneEnd)
    _getFluxCorr_xtra = recipe.add_item(n.getFluxCorr_xtra, after=_ifLevLTmaxBegin)
    _corrSoln = recipe.add_item(n.corrSoln, after=_getFluxCorr_xtra)
    _ifLevLTmaxEnd = recipe.add_item(n.ifLevLTmaxEnd, after=_corrSoln)

    _blockEnd = recipe.add_item(n.blockEnd, after=_ifLevLTmaxEnd)
    # end blocks

    _levelEnd = recipe.add_item(n.levelEnd, after=_blockEnd)
    # end levels

    return recipe


def pm_tele(recipe, root):
    from _spark_nodes import spark_paramesh_tele_nodes

    n = spark_paramesh_tele_nodes()

    _fillGC = recipe.add_item(n.fillGC, after=root)

    # blocks
    _blockBegin = recipe.add_item(n.blockBegin, after=_fillGC)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # stages
    _stageBegin = recipe.add_item(n.stageBegin, after=_stageInit)
    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageBegin, n)
    # end stages
    _stageEnd = recipe.add_item(n.stageEnd, after=_innerStage)

    _putFlux = recipe.add_item(n.putFlux, after=_stageEnd)

    _blockEnd = recipe.add_item(n.blockEnd, after=_putFlux)
    # end blocks

    # TODO: missing if(hy_fluxCorrect) here
    _commFluxes = recipe.add_item(n.commFluxes, after=_blockEnd)
    # second blocks
    _blockBegin2 = recipe.add_item(n.blockBegin2, after=_commFluxes)
    _getFluxCorr_block = recipe.add_item(n.getFluxCorr_block, after=_blockBegin2)
    _corrSoln = recipe.add_item(n.corrSoln, after=_getFluxCorr_block)
    _blockEnd2 = recipe.add_item(n.blockEnd2, after=_corrSoln)
    # end second blocks

    return recipe


def pm_nontele(recipe, root):
    from _spark_nodes import spark_paramesh_nontele_nodes

    n = spark_paramesh_nontele_nodes()

    _stageBegin = recipe.add_item(n.stageBegin, after=root)
    _fillGC = recipe.add_item(n.fillGC, after=_stageBegin)
    _blockBegin = recipe.add_item(n.blockBegin, after=_fillGC)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    # common nodes inner stage loop
    _innerStage = _spark_stage(recipe, _stageInit, n)

    _putFlux = recipe.add_item(n.putFlux, after=_innerStage)
    _saveSoln = recipe.add_item(n.saveSoln, after=_innerStage)

    _blockEnd = recipe.add_item(n.blockEnd, after=_saveSoln)
    _stageEnd = recipe.add_item(n.stageEnd, after=_blockEnd)


    # TODO: missing if(hy_fluxCorrect) here
    _commFluxes = recipe.add_item(n.commFluxes, after=_stageEnd)
    # second blocks
    _blockBegin2 = recipe.add_item(n.blockBegin2, after=_commFluxes)
    _getFluxCorr_block = recipe.add_item(n.getFluxCorr_block, after=_blockBegin2)
    _corrSoln = recipe.add_item(n.corrSoln, after=_getFluxCorr_block)
    _blockEnd2 = recipe.add_item(n.blockEnd2, after=_corrSoln)
    # end second blocks


    return recipe


def test(recipe, root):
    from _spark_nodes import spark_paramesh_nontele_nodes

    n = spark_paramesh_nontele_nodes()

    _stageBegin = recipe.add_item(n.stageBegin, after=root)
    _fillGC = recipe.add_item(n.fillGC, after=_stageBegin)
    _blockBegin = recipe.add_item(n.blockBegin, after=_fillGC)

    # common nodes before stage loop
    _stageInit = _spark_stage_init(recipe, _blockBegin, n)

    _blockEnd = recipe.add_item(n.blockEnd, after=_stageInit)
    _stageEnd = recipe.add_item(n.stageEnd, after=_blockEnd)

    return recipe


def main(variant):
    # create empty recipe
    recipe = flashx.OperationRecipe(tpl="cg-tpl.Hydro.F90")

    if variant == "amrex_tele":
        recipe = amrex_tele(recipe, recipe.root)
    elif variant == "pm_tele":
        recipe = pm_tele(recipe, recipe.root)
    elif variant == "pm_nontele":
        recipe = pm_nontele(recipe, recipe.root)
    elif variant == "test":
        recipe = test(recipe, recipe.root)
    else:
        raise ValueError("invalid variant")

    recipe.verbose = True

    # plot
    # set constants
    PLOTID_GRAPH = 111

    fig = plt.figure(figsize=(16, 6))

    ax = plt.subplot(PLOTID_GRAPH)
    ax.set_title("Control Flow Graph")
    recipe.plot(nodeLabels=True)

    # plt.show()

    fig.savefig(f"__graphs_{variant}.pdf")

    recipe.parse_operation_codes(
        name = f"__Hydro_{variant}",
        templatePath="cg-tpl",
    )



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("variant", type=str, choices=["amrex_tele", "pm_tele", "pm_nontele", "test"])
    args = parser.parse_args()

    main(args.variant)


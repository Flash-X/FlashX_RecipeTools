from FlashX_RecipeTools.nodes import (
    WorkNode,
    SetupNode,
    construct_begin_end_nodes
)


class spark_nodes:
    def __init__(self):

        # begin, end
        self.stageBegin, self.stageEnd = construct_begin_end_nodes(
            name="stage", tpl="cg-tpl.do_stages.json"
        )

        # setups (plain code)
        self.saveFluxBuf = WorkNode(
            name="hy_rk_saveFluxBuf",
            args=[
                "stage", "hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ",
                "&\n   hy_flx", "hy_fly", "hy_flz",
                "&\n   hy_fareaX", "hy_fareaY", "hy_fareaZ",
                "&\n   blkLimits", "lo", "loGC",
            ]
        )

        # work nodes
        self.fillGC = WorkNode(
            name="Grid_fillGuardCells",
            args=[
                "CENTER", "ALLDIR", "doEos=.true.", "eosMode=hy_eosModeGc",
                "&\n   maskSize=NUNK_VARS", "mask=hy_gcMask",
                "&\n   makeMaskConsistent=.true.",
                "&\n   selectBlockType=LEAF",
                "&\n   doLogMask=.NOT. gcMaskLogged",
            ],
        )
        self.shockDet = WorkNode(
            name="hy_rk_shockDetect",
            args=["Uin", "hy_Vc", "blkLimitsGC", "loGC"])
        self.initSoln = WorkNode(
            name="hy_rk_initSolnScratch",
            args=["stage", "Uin", "hy_starState", "hy_tmpState",
                  "&\n   blkLimits", "blkLimitsGC", "lo", "loGC"]
        )
        self.gravAccel = WorkNode(
            name="hy_rk_getGraveAccel",
            args=["hy_starState", "hy_grav",
                  "&\n   hy_xCenter", "hy_yCenter", "deltas",
                  "&\n   blkLimitsGC", "loGC"
            ],
        )
        self.getFlat = WorkNode(
            name="hy_rk_getFlatteningLimiter",
            args=["stage", "hy_starState", "hy_flat3d", "limits", "loGC"]
        )
        self.getFlux = WorkNode(
            name="hy_rk_getFaceFlux",
            args=[
                "stage", "hy_starState", "hy_flat3d", "hy_flx", "hy_fly", "hy_flz",
                "&\n   limits", "deltas",
                "&\n   hy_rope", "hy_flux", "hy_uPlus", "hy_uMinus",
                "&\n   loGC",
            ],
        )
        self.updSoln = WorkNode(
            name="hy_rk_updateSoln",
            args=[
                "stage", "hy_starState", "hy_tmpState",
                "&\n   hy_grav", "hy_flx", "hy_fly", "hy_flz",
                "&\n   deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n   hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n   dt", "dtOld", "limits", "lo", "loGC",
            ],
        )
        self.reAbund = WorkNode(
            name="hy_rk_renormAbundance",
            args=["blkLimitsGC", "hy_starState", "loGC"]
        )
        self.doEos = WorkNode(
            name="Eos_multiDim",
            args=["MODE_DENS_EI", "limits(:, :, stage)", "hy_starState"],
            startswith="@M hy_DIR_TARGET_update_from([hy_starState, limits])",
            endswith="@M hy_DIR_TARGET_update_to([hy_starState])",
        )
        self.putFlux = WorkNode(
            name="Grid_putFluxData",
            args=[
                "tileDesc",
                "&\n   hy_fluxBufX",
                "&\n   hy_fluxBufY",
                "&\n   hy_fluxBufZ",
                "&\n   blkLimits(LOW,:)",
            ],
            startswith="@M hy_DIR_TARGET_update_from([hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ])",
        )



class spark_amrex_tele_nodes(spark_nodes):

    def __init__(self):

        super().__init__()

        self.blockBegin, self.blockEnd = construct_begin_end_nodes(
            name="block", tpl="cg-tpl.do_blocks_level.json"
        )
        self.levelBegin, self.levelEnd = construct_begin_end_nodes(
            name="level", tpl="cg-tpl.do_levels.json"
        )
        self.stageBegin, self.stageEnd = construct_begin_end_nodes(
            name="stage", tpl="cg-tpl.do_stages.json",
            endswith="@M hy_updateState"
        )

        self.ifLevGToneBegin, self.ifLevGToneEnd = construct_begin_end_nodes(
            name="ifLevGTone", tpl="cg-tpl.if_levGTone.json"
        )
        self.ifLevLTmaxBegin, self.ifLevLTmaxEnd = construct_begin_end_nodes(
            name="ifLevLTmax", tpl="cg-tpl.if_levLTmax.json"
        )

        self.commFluxes = SetupNode(name="commFluxes", tpl="cg-tpl.amrex_communicateFluxes.F90")

        self.getFluxCorr_xtra = WorkNode(
            name="Grid_getFluxCorrData_xtra",
            args=[
                "tileDesc",
                "&\n   hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ",
                "&\n   blkLimits(LOW,:)",
                "&\n   hy_flx(:,xLo:xHi+1,yLo:yHi    ,zLo:zHi    )",
                "&\n   hy_fly(:,xLo:xHi  ,yLo:yHi+K2D,zLo:zHi    )",
                "&\n   hy_flz(:,xLo:xHi  ,yLo:yHi    ,zLo:zHi+K3D)",
            ],
        )
        self.corrSoln = WorkNode(
            name="hy_rk_correctFluxes",
            args=[
                "Uin", "blkLimits",
                "&\n   hy_flx(:,xLo:xHi+1,yLo:yHi    ,zLo:zHi    )",
                "&\n   hy_fly(:,xLo:xHi  ,yLo:yHi+K2D,zLo:zHi    )",
                "&\n   hy_flz(:,xLo:xHi  ,yLo:yHi    ,zLo:zHi+K3D)",
                "&\n   deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n   hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n   hy_geometry",
                "&\n   hy_smallE", "hy_smalldens",
                "&\n   dt", ".false.",
                "&\n   lo", "loGC",
            ],
        )



class spark_paramesh_tele_nodes(spark_nodes):

    def __init__(self):

        super().__init__()

        self.stageBegin, self.stageEnd = construct_begin_end_nodes(
            name="stage", tpl="cg-tpl.do_stages.json",
            endswith="@M hy_updateState"
        )
        self.blockBegin, self.blockEnd = construct_begin_end_nodes(
            name="block", tpl="cg-tpl.do_blocks.json"
        )
        self.blockBegin2, self.blockEnd2 = construct_begin_end_nodes(
            name="block2", tpl="cg-tpl.do_blocks2.json"
        )

        self.commFluxes = SetupNode(name="commFluxes", tpl="cg-tpl.pm4_communicateFluxes.F90")

        self.getFluxCorr_block = WorkNode(
            name="Grid_getFluxCorrData_block",
            args=[
                "tileDesc",
                "&\n   hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ",
                "&\n   blkLimits(LOW,:)",
                "&\n   isFluxDensity=(/.true./)",
            ],
        )
        self.corrSoln = WorkNode(
            name="hy_rk_correctFluxes",
            args=[
                "Uin", "blkLimits",
                "&\n   hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ",
                "&\n   deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n   hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n   hy_geometry",
                "&\n   hy_smallE", "hy_smalldens",
                "&\n   dt", ".false.",
                "&\n   lo", "loGC",
            ],
        )


class spark_paramesh_nontele_nodes(spark_nodes):

    def __init__(self):

        super().__init__()

        self.blockBegin, self.blockEnd = construct_begin_end_nodes(
            name="block", tpl="cg-tpl.do_blocks.json"
        )
        self.blockBegin2, self.blockEnd2 = construct_begin_end_nodes(
            name="block2", tpl="cg-tpl.do_blocks2.json"
        )

        self.putFlux = WorkNode(
            name="Grid_putFluxData_block",
            args=["tileDesc", "hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ", "blkLimits(LOW,:)", "add=hy_addFluxArray(stage)"],
            startswith="@M hy_DIR_TARGET_update_from([hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ])",
        )
        self.commFluxes = SetupNode(
            name="commFluxes",
            tpl="cg-tpl.pm4_communicateFluxes.F90"
        )
        self.saveSoln = SetupNode(
            name="saveSoln",
            tpl="cg-tpl.nontele_saveSoln.F90"
        )

        self.shockDet = WorkNode(
            name="hy_rk_shockDetect",
            args=["Uin", "hy_Vc", "blkLimitsGC", "loGC"],
            startswith="if (stage==1) then",
            endswith="endif"
        )
        self.getFluxCorr_block = WorkNode(
            name="Grid_getFluxCorrData_block",
            args=[
                "tileDesc",
                "&\n   hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ",
                "&\n   blkLimits(LOW,:)",
                "&\n   isFluxDensity=(/.false./)",
            ],
        )
        self.corrSoln = WorkNode(
            name="hy_rk_correctFluxes",
            args=[
                "Uin", "blkLimits",
                "&\n   hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ",
                "&\n   deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n   hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n   hy_geometry",
                "&\n   hy_smallE", "hy_smalldens",
                "&\n   dt", ".true.",
                "&\n   lo", "loGC",
            ],
        )



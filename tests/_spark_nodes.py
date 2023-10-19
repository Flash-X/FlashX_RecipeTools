import FlashX_RecipeTools as fr


class spark_nodes:
    def __init__(self):

        # begin, end
        self.stageBegin, self.stageEnd = fr.ConstructBeginEndNodes(
            name="stage", tpl="cg-tpl.do_stages.json"
        )

        # setups (plain code)
        self.saveFluxBuf = fr.SetupNode(name="saveFluxBuf", tpl="cg-tpl.Hydro_saveFluxBuff.F90")

        # work nodes
        self.fillGC = fr.WorkNode(
            name="Grid_fillGuardCells",
            args=["CENTER", "ALLDIR", "doEos=.false.", "maskSize=NUNK_VARS", "mask=hy_gcMask"],
        )
        self.shockDet = fr.WorkNode(
            name="hy_rk_shockDetect",
            args=["Uin", "blkLimitsGC", "hy_tiny"])
        self.initSoln = fr.WorkNode(
            name="hy_rk_initSolnScratch",
            args=["Uin", "hy_starState", "hy_tmpState", "blkLimitsGC", "stage"]
        )
        self.permLims = fr.WorkNode(
            name="hy_rk_permutateLimits",
            args=["blkLimits", "blkLimitsGC", "lim", "limgc"]
        )
        self.gravAccel = fr.WorkNode(
            name="hy_rk_getGraveAccel",
            args=["hy_starState", "hy_grav",
                  "&\n hy_xCenter", "hy_yCenter", "deltas", "hy_geometry", "blkLimitsGC"
            ],
        )
        self.calcLims = fr.WorkNode(
            name="hy_rk_calcLimits",
            args=["stage", "blkLimits", "limits"]
        )
        self.getFlat = fr.WorkNode(
            name="hy_rk_getFlatteningLimiter",
            args=["hy_flattening", "hy_starState", "hy_flat3d", "limits"]
        )
        self.getFlux = fr.WorkNode(
            name="hy_rk_getFaceFlux",
            args=[
                "hy_starState", "hy_flat3d", "hy_flx", "hy_fly", "hy_flz",
                "&\n lim", "limgc", "stage",
                "&\n hy_hybridRiemann", "hy_cvisc", "hy_C_hyp",
                "&\n hy_tiny", "hy_smalldens", "hy_smallpres", "hy_smallX",
                "&\n hya_flux", "hya_flat", "hya_shck", "hya_rope", "hya_uPlus", "hya_uMinus",
            ],
        )
        self.updSoln = fr.WorkNode(
            name="hy_rk_updateSoln",
            args=[
                "hy_starState", "hy_tmpState", "rk_coeffs",
                "&\n hy_grav", "hy_flx", "hy_fly", "hy_flz",
                "&\n deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n hy_geometry",
                "&\n hy_smallE", "hy_smalldens", "hy_alphaGLM", "hy_C_hyp",
                "&\n dt", "dtOld", "limits",
            ],
        )
        self.reAbund = fr.WorkNode(
            name="hy_rk_renormAbundance",
            args=["blkLimitsGC", "hy_starState", "hy_smallX"]
        )
        self.doEos = fr.WorkNode(
            name="Eos_wrapped",
            args=["MODE_DENS_EI", "limits", "hy_starState"]
        )
        self.putFlux = fr.WorkNode(
            name="Grid_putFluxData",
            args=["tileDesc", "hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ", "blkLimits(LOW,:)"]
        )



class spark_amrex_tele_nodes(spark_nodes):

    def __init__(self):

        super().__init__()

        self.blockBegin, self.blockEnd = fr.ConstructBeginEndNodes(
            name="block", tpl="cg-tpl.do_blocks_level.json"
        )
        self.levelBegin, self.levelEnd = fr.ConstructBeginEndNodes(
            name="level", tpl="cg-tpl.do_levels.json"
        )

        self.ifLevGToneBegin, self.ifLevGToneEnd = fr.ConstructBeginEndNodes(
            name="ifLevGTone", tpl="cg-tpl.if_levGTone.json"
        )
        self.ifLevLTmaxBegin, self.ifLevLTmaxEnd = fr.ConstructBeginEndNodes(
            name="ifLevLTmax", tpl="cg-tpl.if_levLTmax.json"
        )

        self.commFluxes = fr.SetupNode(name="commFluxes", tpl="cg-tpl.amrex_communicateFluxes.F90")

        self.getFluxCorr_xtra = fr.WorkNode(
            name="Grid_getFluxCorrData_xtra",
            args=[
                "tileDesc",
                "&\n hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ",
                "&\n blkLimits(LOW,:)",
                "&\n hy_flx(:,xLo:xHi+1,yLo:yHi    ,zLo:zHi    )",
                "&\n hy_fly(:,xLo:xHi  ,yLo:yHi+K2D,zLo:zHi    )",
                "&\n hy_flz(:,xLo:xHi  ,yLo:yHi    ,zLo:zHi+K3D)",
            ],
        )
        self.corrSoln = fr.WorkNode(
            name="hy_rk_correctFluxes",
            args=[
                "Uin", "blkLimits",
                "&\n hy_flx", "hy_fly", "hy_flz",
                "&\n deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n hy_geometry",
                "&\n hy_smallE", "hy_smalldens",
                "&\n dt", "isFlux=.false.",
            ],
        )



class spark_paramesh_tele_nodes(spark_nodes):

    def __init__(self):

        super().__init__()

        self.blockBegin, self.blockEnd = fr.ConstructBeginEndNodes(
            name="block", tpl="cg-tpl.do_blocks.json"
        )

        self.blockBegin2, self.blockEnd2 = fr.ConstructBeginEndNodes(
            name="block2", tpl="cg-tpl.do_blocks2.json"
        )

        self.commFluxes = fr.SetupNode(name="commFluxes", tpl="cg-tpl.pm4_communicateFluxes.F90")

        self.getFluxCorr_block = fr.WorkNode(
            name="Grid_getFluxCorrData_block",
            args=[
                "tileDesc",
                "&\n hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ",
                "&\n blkLimits(LOW,:)",
                "&\n isFluxDensity=(/.true./)",
            ],
        )
        self.corrSoln = fr.WorkNode(
            name="hy_rk_correctFluxes",
            args=[
                "Uin", "blkLimits",
                "&\n hy_fluxBufX", "hy_fluxBufY", "hy_fluxBufZ",
                "&\n deltas", "hy_fareaX", "hy_fareaY", "hy_fareaZ", "hy_cvol", "hy_xCenter",
                "&\n hy_xLeft", "hy_xRight", "hy_yLeft", "hy_yRight",
                "&\n hy_geometry",
                "&\n hy_smallE", "hy_smalldens",
                "&\n dt", "isFlux=.false.",
            ],
        )

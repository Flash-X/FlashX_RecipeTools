import FlashX_RecipeTools as fr


class simpleUnsplit_nodes:

    def __init__(self):

        self.tileBegin, self.tileEnd = fr.ConstructTileLoop()

        self.soundSpd = fr.WorkNode(
            name = "Hydro_computeSoundSpeedHll",
            args = ["lo", "hi", "U", "auxC"],
        )

        self.flx = fr.WorkNode(
            name = "Hydro_computeFluxesHll_X",
            args = ["dt", "lo", "hi", "deltas", "U", "auxC", "flX"],
        )
        self.fly = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Y",
            args = ["dt", "lo", "hi", "deltas", "U", "auxC", "flY"],
        )
        self.flz = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Z",
            args = ["dt", "lo", "hi", "deltas", "U", "auxC", "flZ"],
        )
        self.tst = fr.WorkNode(
            name = "tst",
            args = ["dt", "lo", "hi", "deltas", "U", "auxC", "flZ"],
        )

        self.updSoln = fr.WorkNode(
            name = "Hydro_updateSolutionHll",
            args = ["lo", "hi", "flX", "flY", "flZ", "U"],
        )

        self.doEos = fr.WorkNode(
            name="Eos_wrapped",
            args=["MODE_DENS_EI", "limits", "U"]
        )

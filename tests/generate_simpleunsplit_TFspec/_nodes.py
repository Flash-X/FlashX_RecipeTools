import FlashX_RecipeTools as fr


class simpleUnsplit_nodes:

    def __init__(self):

        self.tileBegin, self.tileEnd = fr.ConstructTileLoop()

        self.soundSpd = fr.WorkNode(
            name = "Hydro_computeSoundSpeedHll",
            opspec = "Hydro_op1",
        )

        self.flx = fr.WorkNode(
            name = "Hydro_computeFluxesHll_X",
            opspec = "Hydro_op1",
        )
        self.fly = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Y",
            opspec = "Hydro_op1",
        )
        self.flz = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Z",
            opspec = "Hydro_op1",
        )

        self.updSoln = fr.WorkNode(
            name = "Hydro_updateSolutionHll",
            opspec = "Hydro_op1",
        )

        self.doEos = fr.WorkNode(
            name = "Eos_wrapped",
            opspec = "Hydro_op1",
        )

        self.tst1 = fr.WorkNode(
            name = "test_1",
            args = ["a", "b", "c"],
            opspec = "Hydro_op1",
        )
        self.tst2 = fr.WorkNode(
            name = "test_2",
            args = ["a", "b", "c"],
            opspec = "Hydro_op1",
        )

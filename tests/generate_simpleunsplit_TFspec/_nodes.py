import FlashX_RecipeTools as fr


class simpleUnsplit_nodes:

    def __init__(self):

        self.tileBegin, self.tileEnd = fr.ConstructTileLoop()

        self.soundSpd = fr.WorkNode(
            name = "Hydro_computeSoundSpeedHll",
        )

        self.flx = fr.WorkNode(
            name = "Hydro_computeFluxesHll_X",
        )
        self.fly = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Y",
        )
        self.flz = fr.WorkNode(
            name = "Hydro_computeFluxesHll_Z",
        )

        self.updSoln = fr.WorkNode(
            name = "Hydro_updateSolutionHll",
        )

        self.doEos = fr.WorkNode(
            name="Eos_wrapped",
        )

        self.tst1 = fr.WorkNode(
            name = "test_1",
            args = ["a", "b", "c"],
        )
        self.tst2 = fr.WorkNode(
            name = "test_2",
            args = ["a", "b", "c"],
        )

import FlashX_RecipeTools as flashx

import filecmp
from pathlib import Path

CWD = Path(__file__).parent.absolute()
REF_PATH = CWD / Path("ref")

def load_recipe(objdir):

    recipe = flashx.TimeStepRecipe(flashx_objdir=objdir)

    hydro_begin = recipe.begin_orchestration(itor_type="LEAF", after=recipe.root)
    hydro_prepBlock = recipe.add_work("Hydro_prepBlock", after=hydro_begin, map_to="gpu")
    hydro_advance = recipe.add_work("Hydro_advance", after=hydro_prepBlock, map_to="gpu")
    hydro_end = recipe.end_orchestration(hydro_begin, after=hydro_advance)

    return recipe


def test_spark_hydro():

    recipe = load_recipe(CWD)

    destination = CWD / "__milhoja_codes"

    ir = recipe.compile()
    ir.generate_all_codes(dest = destination)

    # testing: all expected files should be generated
    actual_generated_files = {file.name for file in Path(destination).iterdir()}
    expect_generated_files = recipe.get_output_fnames()
    assert len(expect_generated_files.difference(actual_generated_files)) == 0

    # testing: generated files should be identical to reference files
    # TODO: the argument ordering for external (maybe) variables are not consistent
    #       this assertion may pass or not. -> fix in milhoja_pypkg
    for file in expect_generated_files:
        actual = destination / file
        expected = REF_PATH / file

        assert filecmp.cmp(actual, expected, shallow=False), (
            f"Files are not identical: {actual.name}" + "\n"
            f"actual   : {actual}" + "\n"
            f"expected : {expected}"
        )



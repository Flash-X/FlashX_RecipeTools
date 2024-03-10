import FlashX_RecipeTools as flashx

import filecmp
from pathlib import Path

CWD = Path(__file__).parent.absolute()
REF_PATH = CWD / Path("ref")

def load_recipe():

    recipe = flashx.TimeStepRecipe()

    hydro_begin = recipe.begin_orchestration(itor_type="LEAF", after=recipe.root)
    hydro_prepBlock = recipe.add_work("Hydro_prepBlock", after=hydro_begin, map_to="gpu")
    hydro_advance = recipe.add_work("Hydro_advance", after=hydro_prepBlock, map_to="gpu")
    hydro_end = recipe.end_orchestration(hydro_begin, after=hydro_advance)

    return recipe


def test_spark_hydro():

    recipe = load_recipe()
    # writes all needed operation specs by processing interface files
    recipe.collect_operation_specs()

    tf_data_all = flashx.compile_recipe(recipe)

    destination = "__milhoja_codes"
    for tf_data in tf_data_all:
        flashx.generate_taskfunction_codes(tf_data, dest=destination)

    actual_generated_files = {file.name for file in Path(destination).iterdir()}
    expect_generated_files = recipe.get_output_fnames()

    # all expected files should be generated
    assert len(expect_generated_files.difference(actual_generated_files)) == 0

    # check if generated files are identical to reference files
    # TODO: the argument ordering for external (maybe) variables are not consistent
    #       this assertion may pass or not. -> fix in milhoja_pypkg
    for file in expect_generated_files:
        actual = Path(destination) / file
        expected = REF_PATH / file

        print(f"checking {actual} == {expected}")
        assert filecmp.cmp(actual, expected, shallow=False)



import FlashX_RecipeTools as flashx
from loguru import logger
import sys


def load_recipe(dimension):

    recipe = flashx.TimeStepRecipe()

    # assuming [spec_name]::[function_name] format

    hydro_begin = recipe.begin_orchestration(itor_type="LEAF", after=recipe.root)
    sound_speed = recipe.add_work("Hydro_op1::Hydro_computeSoundSpeedHll", after=hydro_begin, map_to="gpu")
    comp_flx = recipe.add_work("Hydro_op1::Hydro_computeFluxesHll_X", after=sound_speed, map_to="gpu")
    comp_fly = recipe.add_work("Hydro_op1::Hydro_computeFluxesHll_Y", after=comp_flx, map_to="gpu")
    if dimension == 2:
        update_soln = recipe.add_work("Hydro_op1::Hydro_updateSolutionHll", after=comp_fly, map_to="gpu")
    elif dimension == 3:
        comp_flz = recipe.add_work("Hydro_op1::Hydro_computeFluxesHll_Z", after=comp_fly, map_to="gpu")
        update_soln = recipe.add_work("Hydro_op1::Hydro_updateSolutionHll", after=comp_flz, map_to="gpu")
    else:
        raise ValueError("Invalid dimension for recipe")
    do_eos = recipe.add_work("Hydro_op1::Eos_wrapped", after=update_soln, map_to="gpu")
    hydro_end = recipe.end_orchestration(hydro_begin, after=do_eos)

    return recipe

# ./setup Sedov -auto -2d -objdir=testing --recipe=recipe.py

if __name__ == "__main__":

    logger.remove(0)
    logger.add(sys.stdout, level=0)
    logger.enable(flashx.__name__)

    #TODO: reorder variable names by interacting with setup.py
    #      this will *re-generate* files including Simulation.h
    #      how?


    recipe = load_recipe(dimension=2)


    #TODO: read Simulation.h and write grid_spec
    #      utils.header2dict

    recipe.add_group_specs()   # TODO: read each operation specs defined in setup_operationSpecs

    tf_data_all = flashx.compile_recipe(recipe)

    for tf_data in tf_data_all:
        flashx.generate_taskfunction_codes(tf_data)


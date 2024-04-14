import milhoja
import json
import re
import os
from pathlib import Path
from loguru import logger

from .construct_partial_tf_spec import construct_partial_tf_spec

from ..utils import MakefileParser

def find_milhoja_path(objdir):
    """
    Find the Milhoja installation path by searching
    "MILHOJA_PATH" macro in the Makefile.h and return its value
    """

    # parse "Makefile" also, in order to resolve macros defined in there. e.g., NDIM
    makefile = MakefileParser([objdir / "Makefile", objdir / "Makefile.h"])
    milhoja_path = makefile.expand_macro("MILHOJA_PATH")

    # if found string is a relative path,
    # assuming it is relative to makefile_site
    # TODO: this is only for test case
    if not Path(milhoja_path).is_absolute():
        return objdir / milhoja_path

    if Path(milhoja_path).is_dir():
        return milhoja_path

    # if it reaches here, something went wrong
    raise ValueError(f"Unable to resolve the MILHOJA_PATH = {milhoja_path}")


def generate_grid_json(simulation_h_path:Path, grid_json_path:Path) -> dict:
    """
    Reads Simulation.h and write the grid information
    needed for Milhoja to JSON format.
    """
    if not simulation_h_path.is_file():
        raise FileNotFoundError(f"{simulation_h_path} is not found in the current directory")
    # the regex pattern to match lines with '#define KEY VALUE'
    pattern = r"^\s*#define\s+(\w+)\s+(\S+)"
    # Mapping of C preprocessor keys to output dictionary keys
    key_map = {
        "NDIM": "dimension",
        "NXB": "nxb",
        "NYB": "nyb",
        "NZB": "nzb",
        "NGUARD": "nguardcells",
    }
    out_dict = {}
    with open(simulation_h_path, 'r') as fptr:
        for line in fptr:
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                key, value = match.groups()
                if key in key_map:
                    # Convert value to an integer
                    try:
                        value = int(value)
                    except ValueError:
                        raise RuntimeError(f"Unable to cast {value} to intger in processing [{line}].")
                    if key_map[key] in out_dict:
                        raise RuntimeError(f"Multiple definitions for {key} are detected")
                    out_dict[key_map[key]] = value

    # write to disk
    if grid_json_path.is_file():
        logger.warning("Overwriting {_file}", _file=grid_json_path)
    with open(grid_json_path, 'w') as fptr:
        json.dump(out_dict, fptr, indent=2)

    return out_dict


def generate_taskfunction_codes(tf_data, dest="__milhoja"):
    # TODO: check if tf_data is valid

    tf_name = tf_data["name"]
    objdir = Path(tf_data["objdir"])

    # construct partial tf spec
    partial_tf_spec = construct_partial_tf_spec(tf_data)

    partial_tf_json = objdir / f"__{tf_name}.json"
    with open(partial_tf_json, "w") as fptr:
        json.dump(partial_tf_spec, fptr, indent=2)

    grid_json = objdir / "__grid.json"
    simulation_h = objdir / "Simulation.h"
    grid_spec = generate_grid_json(simulation_h, grid_json)

    # Milhoja
    milhoja_logger = milhoja.BasicLogger(level=3)

    call_graph = tf_data["subroutine_call_graph"]
    group_json_all = tf_data["operation_specs"]
    tfAssembler = milhoja.TaskFunctionAssembler.from_milhoja_json(
        tf_name, call_graph, group_json_all, grid_json, milhoja_logger
    )

    tf_spec_json = objdir / f"__tf_spec_{tf_name}.json"
    tfAssembler.to_milhoja_json(tf_spec_json, partial_tf_json, overwrite=True)

    # Write task function's code for use with Orchestration unit

    destination = objdir / dest
    if destination.is_file():
        logger.error("Destination path {_destination} is a file", _destination=destination)
        raise FileExistsError(destination)

    if not destination.is_dir():
        logger.info("Making directory at {_destination}", _destination=destination)
        destination.mkdir(parents=True, exist_ok=True)

    overwrite = True
    indent = 3
    milhoja_path = find_milhoja_path(objdir)

    tf_spec = milhoja.TaskFunction.from_milhoja_json(tf_spec_json)

    # TODO: not implmented yet. (branch: 63-datapacketgenerator-lacks-lbound-support)
    milhoja.generate_data_item(
        tf_spec, destination, overwrite, milhoja_path, indent, milhoja_logger
    )

    # TODO: not implmented yet. (branch: FortranOaccTf)
    milhoja.generate_task_function(
        tf_spec, destination, overwrite, indent, milhoja_logger
    )

    return


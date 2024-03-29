import milhoja
import json
import re
import os
from pathlib import Path
from loguru import logger

from .construct_partial_tf_spec import construct_partial_tf_spec

# TODO: better implementation for this
def find_milhoja_path(makefile_site, grid_spec):
    _MILHOJA_PATH_PATTERN = re.compile(r"(MILHOJA_PATH)\s+=\s+(?P<path>\S+)")
    with open(makefile_site, "r") as f:
        for line in f.readlines():
            match = re.match(_MILHOJA_PATH_PATTERN, line)
            if match:
                break

    if not match:
        raise KeyError("MILHOJA_PATH is not found in Makefile.h")

    milhoja_path_from_make = match.group("path")

    # if the found string is env variable
    if milhoja_path_from_make.startswith("$"):
        # process ${NDIM}
        _NDIM_PATTERN = re.compile(r"\$(\(|{)(\s*NDIM\s*)(}|\))")
        milhoja_path_from_make = re.sub(
            _NDIM_PATTERN, f"{grid_spec['dimension']}", milhoja_path_from_make
        )
        # resolve environment variable TODO: recursive?
        _ENV_NAME = re.compile(r"\$(\(|{)(?P<env_name>\s*\S+\s*)(}|\))")
        match = re.match(_ENV_NAME, milhoja_path_from_make)
        milhoja_path = os.environ[match.group("env_name")]

        if not Path(milhoja_path).is_dir():
            raise ValueError(f"Failed to resolve environment variable {milhoja_path}")

        return milhoja_path

    # if found string is a relative path,
    # assuming it is relative to makefile_site
    # TODO: this is only for test case
    if not Path(milhoja_path_from_make).is_absolute():
        return makefile_site.parent / milhoja_path_from_make

    if Path(milhoja_path_from_make).is_dir():
        return milhoja_path_from_make


    # if it reaches here, something went wrong
    raise ValueError(f"Unable to resolve the MILHOJA_PATH = {milhoja_path_from_make}, found in {makefile_site}")


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
    milhoja_path = find_milhoja_path(objdir / "Makefile.h", grid_spec)

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


import milhoja
import json
import re
import os
from pathlib import Path
from loguru import logger


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

    if Path(milhoja_path_from_make).is_dir():
        return milhoja_path_from_make

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


def generate_grid_json(grid_json_filepath:str) -> dict:
    """
    Reads Simulation.h and write the grid information
    needed for Milhoja to JSON format.
    """
    simulation_h = Path("Simulation.h")
    if not simulation_h.is_file():
        raise FileNotFoundError("Simulation.h is not found in the current directory")
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
    with open(simulation_h, 'r') as fptr:
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
    if Path(grid_json_filepath).is_file():
        logger.warning("Overwriting {_file}", _file=grid_json_filepath)
    with open(grid_json_filepath, 'w') as fptr:
        json.dump(out_dict, fptr, indent=2)

    return out_dict


def generate_taskfunction_codes(tf_data):
    # TODO: check if tf_data is valid

    tf_name = tf_data["name"]
    processor = tf_data["processor"]

    # TODO: this may be in tfData
    data_item = "TileWrapper"
    offloading = ""
    if processor.lower() == "gpu":
        data_item = "DataPacket"
        # TODO: openmp offload?
        offloading = "OpenACC"

    tf_partial_spec = {
        "task_function": {
            "language": "Fortran",
            "processor": processor,
            "computation_offloading": offloading,
            "variable_index_base": 1,
            "cpp_header": f"{tf_name}.h",
            "cpp_source": f"{tf_name}.cxx",
            "c2f_source": f"{tf_name}_C2F.F90",
            "fortran_source": f"{tf_name}_mod.F90",
        },
        "data_item": {
            "type": data_item,
            "byte_alignment": 1,
            "header": f"{data_item}_{tf_name}.h",
            "module": f"{data_item}_{tf_name}_mod.F90",
            "source": f"{data_item}_{tf_name}.cxx",
        },
    }

    tf_partial_json = f"__{tf_name}.json"
    with open(tf_partial_json, "w") as fptr:
        json.dump(tf_partial_spec, fptr, indent=2)

    grid_json = "__grid.json"
    grid_spec = generate_grid_json(grid_json)

    # Milhoja
    logger = milhoja.BasicLogger(level=3)

    call_graph = tf_data["subroutine_call_graph"]
    group_json_all = tf_data["operation_specs"]
    tfAssembler = milhoja.TaskFunctionAssembler.from_milhoja_json(
        tf_name, call_graph, group_json_all, grid_json, logger
    )

    tf_spec_json = f"__tf_spec_{tf_name}.json"
    tfAssembler.to_milhoja_json(tf_spec_json, tf_partial_json, overwrite=True)

    # Write task function's code for use with Orchestration unit

    destination = Path("./__milhoja")
    overwrite = True
    indent = 3
    milhoja_path = find_milhoja_path("Makefile.h", grid_spec)

    tf_spec = milhoja.TaskFunction.from_milhoja_json(tf_spec_json)

    # TODO: not implmented yet. (branch: 63-datapacketgenerator-lacks-lbound-support)
    milhoja.generate_data_item(
        tf_spec, destination, overwrite, milhoja_path, indent, logger
    )

    # TODO: not implmented yet. (branch: FortranOaccTf)
    milhoja.generate_task_function(
        tf_spec, destination, overwrite, indent, logger
    )

    return

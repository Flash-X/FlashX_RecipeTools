#!/usr/bin/env python3
"""Generate the 2D HOSTMEM TaskFunction and DataPacket for NewImpl face flux."""

import argparse
import json
import shutil

from pathlib import Path

import milhoja

from FlashX_RecipeTools import ArithmeticHelperContract, ComputationSourceGenerator
from FlashX_RecipeTools.TimeStepRecipe.construct_partial_tf_spec import construct_partial_tf_spec
from layout_config import (
    LAYOUT_CHOICES, VARIABLE_FIRST, VARIABLE_LAST, adapter_source,
    layout_binding,
)


HERE = Path(__file__).resolve().parent
TASK_FUNCTION_NAME = "newimpl_face_flux_tf"
ADAPTER_NAME = "newimpl_face_flux_adapter"


def _write_json(path, data, overwrite):
    if path.exists() and not overwrite:
        raise FileExistsError("Output already exists: {!s}".format(path))
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _copy(path, destination, overwrite):
    if destination.exists() and not overwrite:
        raise FileExistsError("Output already exists: {!s}".format(destination))
    shutil.copyfile(path, destination)


def _group_specification(nxb, nyb, layout):
    if layout == VARIABLE_FIRST:
        flat_extents = "(1, {}, {}, 1)".format(nxb + 2, nyb + 2)
        reconstructed_extents = "(7, {}, {}, 1)".format(nxb + 2, nyb + 2)
        flat_lbound = "(1, tile_lo(1)-1, tile_lo(2)-1, tile_lo(3))"
        reconstructed_lbound = flat_lbound
    else:
        flat_extents = "({}, {}, 1, 1)".format(nxb + 2, nyb + 2)
        reconstructed_extents = "({}, {}, 1, 7)".format(nxb + 2, nyb + 2)
        flat_lbound = "(tile_lo(1)-1, tile_lo(2)-1, tile_lo(3), 1)"
        reconstructed_lbound = flat_lbound
    scratch = {
        "_flat": {
            "type": "real",
            "extents": flat_extents,
            "lbound": flat_lbound,
        },
        "_reconstructed_minus": {
            "type": "real",
            "extents": reconstructed_extents,
            "lbound": reconstructed_lbound,
        },
        "_reconstructed_plus": {
            "type": "real",
            "extents": reconstructed_extents,
            "lbound": reconstructed_lbound,
        },
        "_max_speed": {"type": "real", "extents": "(1)", "lbound": "(1)"},
        "_status": {"type": "integer", "extents": "(1)", "lbound": "(1)"},
        "_failed_face": {"type": "integer", "extents": "(4)", "lbound": "(1)"},
    }
    external = {
        "_density_floor": {"type": "real", "extents": "()"},
        "_pressure_floor": {"type": "real", "extents": "()"},
        "_tiny_state": {"type": "real", "extents": "()"},
        "_viscosity": {"type": "real", "extents": "()"},
        "_weno_epsilon": {"type": "real", "extents": "()"},
        "_flattening_eta": {"type": "real", "extents": "()"},
        "_flattening_flag": {"type": "integer", "extents": "()"},
        "_hybrid_flag": {"type": "integer", "extents": "()"},
        "_shock_marker_flag": {"type": "integer", "extents": "()"},
        "_ndim": {"type": "integer", "extents": "()"},
    }

    argument_list = [
        "tile_lo", "tile_hi", "tile_lbound", "state", "flux_x", "flux_y",
        "flat", "reconstructed_minus", "reconstructed_plus",
        "density_floor", "pressure_floor", "tiny_state", "viscosity",
        "weno_epsilon", "flattening_eta", "flattening_flag", "hybrid_flag",
        "shock_marker_flag", "ndim", "max_speed", "status", "failed_face",
    ]
    arguments = {
        "tile_lo": {"source": "tile_lo"},
        "tile_hi": {"source": "tile_hi"},
        "tile_lbound": {"source": "tile_lbound"},
        "state": {
            "source": "grid_data",
            "structure_index": ["CENTER", 1],
            "r": list(range(1, 9)),
        },
        "flux_x": {
            "source": "grid_data",
            "structure_index": ["FLUXX", 1],
            "w": list(range(1, 6)),
        },
        "flux_y": {
            "source": "grid_data",
            "structure_index": ["FLUXY", 1],
            "w": list(range(1, 6)),
        },
    }
    for name in (
        "flat", "reconstructed_minus", "reconstructed_plus",
        "max_speed", "status", "failed_face",
    ):
        arguments[name] = {"source": "scratch", "name": "_{}".format(name)}
    for name in (
        "density_floor", "pressure_floor", "tiny_state", "viscosity",
        "weno_epsilon", "flattening_eta", "flattening_flag", "hybrid_flag",
        "shock_marker_flag", "ndim",
    ):
        arguments[name] = {"source": "external", "name": "_{}".format(name)}

    return {
        "format": ["Milhoja-JSON", "1.0.0"],
        "name": "newimpl_face_flux",
        "variable_index_base": 1,
        "external": external,
        "scratch": scratch,
        ADAPTER_NAME: {
            "interface_file": "newimpl_face_flux_adapter_mod.F90",
            "argument_list": argument_list,
            "argument_specifications": arguments,
        },
    }


def _contract_mapping(layout):
    return {
        "data_layout": {
            "packet": layout,
            "tile_source": VARIABLE_LAST,
        },
        "state": {"task_function_argument": "CC_1", "access": "input", "variables": [1, 8]},
        "face_flux": {
            "task_function_arguments": ["FLX_1", "FLY_1"],
            "access": "output",
            "variables": [1, 5],
        },
        "input_map": {"adapter_constant": [1, 2, 3, 4, 5, 6, 7]},
        "output_map": {"adapter_constant": [1, 2, 3, 4, 5]},
        "parameters": {
            "external_scalars": [
                "density_floor", "pressure_floor", "tiny_state", "viscosity",
                "weno_epsilon", "flattening_eta", "flattening_flag",
                "hybrid_flag", "shock_marker_flag", "ndim",
            ]
        },
        "flattening": {"scratch": "scratch_newimpl_face_flux_flat"},
        "reconstructed_minus": {"scratch": "scratch_newimpl_face_flux_reconstructed_minus"},
        "reconstructed_plus": {"scratch": "scratch_newimpl_face_flux_reconstructed_plus"},
        "max_speed": {"packet_result_scratch": "scratch_newimpl_face_flux_max_speed"},
        "status": {"packet_result_scratch": "scratch_newimpl_face_flux_status"},
        "failed_face": {"packet_result_scratch": "scratch_newimpl_face_flux_failed_face"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newimpl_source", type=Path)
    parser.add_argument("milhoja_prefix", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--nxb", type=int, default=16)
    parser.add_argument("--nyb", type=int, default=16)
    parser.add_argument(
        "--layout", choices=LAYOUT_CHOICES, default=VARIABLE_LAST,
        help="component ordering inside the generated DataPacket",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.nxb < 1 or args.nyb < 1:
        parser.error("--nxb and --nyb must be positive")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    contract = ArithmeticHelperContract.load(HERE / "newimpl_face_flux.contract.json")
    computation = output / "newimpl_face_flux_milhoja.F90"
    ComputationSourceGenerator(contract).generate(
        args.newimpl_source,
        layout_binding(HERE, args.layout),
        computation,
        overwrite=args.overwrite,
    )
    _copy(
        adapter_source(HERE, args.layout),
        output / "newimpl_face_flux_adapter_mod.F90",
        args.overwrite,
    )

    grid = {
        "dimension": 2,
        "nxb": args.nxb,
        "nyb": args.nyb,
        "nzb": 1,
        "nguardcells": 3,
    }
    group = _group_specification(args.nxb, args.nyb, args.layout)
    partial = construct_partial_tf_spec({
        "name": TASK_FUNCTION_NAME,
        "processor": "CPU",
        "data_item": "DataPacket",
        "computation_offloading": "",
        "byte_alignment": 16,
        "data_layout": args.layout,
    })

    grid_path = output / "newimpl_face_flux.grid.json"
    group_path = output / "newimpl_face_flux.group.json"
    partial_path = output / "newimpl_face_flux.partial.json"
    spec_path = output / "newimpl_face_flux.taskfunction.json"
    mapping_path = output / "newimpl_face_flux.mapping.json"
    _write_json(grid_path, grid, args.overwrite)
    _write_json(group_path, group, args.overwrite)
    _write_json(partial_path, partial, args.overwrite)
    _write_json(mapping_path, _contract_mapping(args.layout), args.overwrite)

    logger = milhoja.BasicLogger(milhoja.LOG_LEVEL_NONE)
    assembler = milhoja.TaskFunctionAssembler.from_milhoja_json(
        TASK_FUNCTION_NAME,
        [ADAPTER_NAME],
        [group_path],
        grid_path,
        logger,
    )
    assembler.to_milhoja_json(spec_path, partial_path, args.overwrite)

    tf_spec = milhoja.TaskFunction.from_milhoja_json(spec_path)
    milhoja.generate_data_item(
        tf_spec, output, args.overwrite, args.milhoja_prefix, 4, logger
    )
    milhoja.generate_task_function(tf_spec, output, args.overwrite, 4, logger)
    print("Generated {} and {} in {}".format(
        tf_spec.name, tf_spec.data_item_class_name, output
    ))


if __name__ == "__main__":
    main()

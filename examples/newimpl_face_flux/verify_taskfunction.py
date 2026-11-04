#!/usr/bin/env python3
"""Verify the NewImpl HOSTMEM TaskFunction generation contract."""

import argparse
import filecmp
import json
import os
import subprocess
import sys
import tempfile

from pathlib import Path

from FlashX_RecipeTools import ArithmeticHelperContract, KernelBoundaryContract
from grouping_config import adapter_names
from layout_config import LAYOUT_CHOICES, VARIABLE_FIRST
from verify_layout_transforms import verify_layout_transforms


HERE = Path(__file__).resolve().parent
GENERATOR = HERE / "generate_taskfunction.py"
TEST_GENERATOR = HERE / "generate_test.py"
EXPECTED_FILES = {
    "DataPacket_newimpl_face_flux_tf.cxx",
    "DataPacket_newimpl_face_flux_tf.h",
    "DataPacket_newimpl_face_flux_tf_mod.F90",
    "cg-tpl.helper_DataPacket_newimpl_face_flux_tf.cpp",
    "cg-tpl.helper_DataPacket_newimpl_face_flux_tf_cpp2c.cpp",
    "cg-tpl.outer_DataPacket_newimpl_face_flux_tf.cpp",
    "cg-tpl.outer_DataPacket_newimpl_face_flux_tf_cpp2c.cpp",
    "newimpl_face_flux.grid.json",
    "newimpl_face_flux.group.json",
    "newimpl_face_flux.grouping.json",
    "newimpl_face_flux.mapping.json",
    "newimpl_face_flux.partial.json",
    "newimpl_face_flux.taskfunction.json",
    "newimpl_face_flux_adapter_mod.F90",
    "newimpl_face_flux_milhoja.F90",
    "newimpl_face_flux_tf.cxx",
    "newimpl_face_flux_tf_C2F.F90",
    "newimpl_face_flux_tf_mod.F90",
}


def _generate(source, prefix, destination, seed, layout, grouping):
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = str(seed)
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            str(source),
            str(prefix),
            str(destination),
            "--layout",
            layout,
            "--grouping",
            grouping,
        ],
        check=True,
        env=environment,
    )


def _verify_standalone_generation(source, destination, layout):
    output = destination / "test_newimpl_face_flux_milhoja.F90"
    subprocess.run(
        [
            sys.executable,
            str(TEST_GENERATOR),
            str(source),
            str(output),
            "--layout",
            layout,
        ],
        check=True,
    )
    generated = output.read_text()
    if "${" in generated:
        raise AssertionError(
            "Standalone {} source contains an unresolved placeholder".format(layout)
        )


def _assert_equal_directories(first, second):
    comparison = filecmp.dircmp(first, second)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        raise AssertionError("Generated file sets differ")
    differing = [
        name
        for name in comparison.common_files
        if not filecmp.cmp(first / name, second / name, shallow=False)
    ]
    if differing:
        raise AssertionError(
            "Nondeterministic generated files: {}".format(", ".join(differing))
        )


def _verify_specification(output, layout, grouping):
    specification = json.loads(
        (output / "newimpl_face_flux.taskfunction.json").read_text()
    )
    task = specification["task_function"]
    data_item = specification["data_item"]
    arguments = task["argument_specifications"]

    assert task["processor"] == "CPU"
    assert task["computation_offloading"] == ""
    assert task["subroutine_call_graph"] == list(
        adapter_names(grouping["name"])
    )
    assert data_item["type"] == "DataPacket"
    assert data_item["byte_alignment"] == 16
    assert data_item["data_layout"] == layout

    mapping = json.loads(
        (output / "newimpl_face_flux.mapping.json").read_text()
    )
    assert mapping["execution"] == {
        "name": "hostmem",
        "processor": "CPU",
        "offloading": "",
    }
    assert mapping["data_layout"] == {
        "packet": layout,
        "tile_source": "variable-last",
    }
    assert mapping["kernel_grouping"]["name"] == grouping["name"]
    assert mapping["kernel_grouping"]["kernel_groups"] == grouping["kernel_groups"]
    assert mapping["kernel_grouping"]["cuts"] == grouping["cuts"]

    selection = json.loads(
        (output / "newimpl_face_flux.grouping.json").read_text()
    )
    assert selection["boundary_contract"] == "newimpl_face_flux_boundaries"
    assert selection["arithmetic_contract"] == "newimpl_face_flux"
    assert selection["selection"] == grouping

    expected_grid = {
        "CC_1": ("CENTER", [1, 8], None),
        "FLX_1": ("FLUXX", None, [1, 5]),
        "FLY_1": ("FLUXY", None, [1, 5]),
    }
    for name, (structure, variables_in, variables_out) in expected_grid.items():
        argument = arguments[name]
        assert argument["source"] == "grid_data"
        assert argument["structure_index"][0] == structure
        assert argument.get("variables_in") == variables_in
        assert argument.get("variables_out") == variables_out

    if layout == VARIABLE_FIRST:
        flat_extents = "(1, 18, 18, 1)"
        reconstructed_extents = "(7, 18, 18, 1)"
    else:
        flat_extents = "(18, 18, 1, 1)"
        reconstructed_extents = "(18, 18, 1, 7)"
    expected_scratch = {
        "scratch_newimpl_face_flux_flat": ("real", flat_extents),
        "scratch_newimpl_face_flux_reconstructed_minus": (
            "real", reconstructed_extents
        ),
        "scratch_newimpl_face_flux_reconstructed_plus": (
            "real", reconstructed_extents
        ),
        "scratch_newimpl_face_flux_max_speed": ("real", "(1)"),
        "scratch_newimpl_face_flux_status": ("integer", "(1)"),
        "scratch_newimpl_face_flux_failed_face": ("integer", "(4)"),
    }
    for name, (datatype, extents) in expected_scratch.items():
        argument = arguments[name]
        assert argument["source"] == "scratch"
        assert argument["type"] == datatype
        assert argument["extents"] == extents

    assert arguments["external_newimpl_face_flux_ndim"] == {
        "type": "integer",
        "extents": "()",
        "source": "external",
    }


def _verify_layout_sources(output, layout):
    c2f = (output / "newimpl_face_flux_tf_C2F.F90").read_text()
    packet = (output / "DataPacket_newimpl_face_flux_tf.cxx").read_text()
    adapter = (output / "newimpl_face_flux_adapter_mod.F90").read_text()

    if layout == VARIABLE_FIRST:
        assert "shape=[8, 16 + 2 * 3 * MILHOJA_K1D" in c2f
        assert "shape=[5, (16 + 1), 16, 1, F_nTiles_h]" in c2f
        assert "shape=[7, 18, 18, 1, F_nTiles_h]" in c2f
        assert "nCells_CC_1" in packet
        assert "CC_1_p[variable + nVars_CC_1 * cell]" in packet
        assert "FLX_1_data_h[cell + nCells_FLX_1 * variable]" in packet
        assert "available_hi = tile_lbound + [size(state, 2)" in adapter
    else:
        assert "shape=[16 + 2 * 3 * MILHOJA_K1D" in c2f
        assert "shape=[(16 + 1), 16, 1, 5, F_nTiles_h]" in c2f
        assert "shape=[18, 18, 1, 7, F_nTiles_h]" in c2f
        assert "nCells_CC_1" not in packet
        assert "std::memcpy(static_cast<void*>(char_ptr)" in packet
        assert "available_hi = tile_lbound + [size(state, 1)" in adapter


def _verify_host_sources(output):
    forbidden = ("!$acc", "use openacc", "cuda")
    for path in output.iterdir():
        if path.suffix.lower() not in {".f90", ".cxx", ".h", ".cpp"}:
            continue
        text = path.read_text().lower()
        for token in forbidden:
            if token in text:
                raise AssertionError("{} contains {!r}".format(path.name, token))


def _verify_grouped_sources(output, grouping):
    computation = (output / "newimpl_face_flux_milhoja.F90").read_text()
    adapter = (output / "newimpl_face_flux_adapter_mod.F90").read_text()
    name = grouping["name"]
    assert computation.count("subroutine hy_getFaceFlux(") == 1
    if name == "fully_fused":
        assert "subroutine hy_faceFluxFlattening(" not in computation
        assert "call hy_getFaceFlux(" in adapter
    elif name == "flattening_then_directional":
        assert computation.count("subroutine hy_faceFluxFlattening(") == 1
        assert computation.count("subroutine hy_faceFluxDirectional(") == 1
        assert "subroutine hy_faceFluxReconstructDirection(" not in computation
        assert adapter.index("call hy_faceFluxFlattening(") < adapter.index(
            "call hy_faceFluxDirectional("
        )
    elif name == "flattening_reconstruction_solve":
        assert computation.count("subroutine hy_faceFluxFlattening(") == 1
        assert computation.count("subroutine hy_faceFluxReconstructDirection(") == 1
        assert computation.count("subroutine hy_faceFluxSolveDirection(") == 1
        flattening = adapter.index("call hy_faceFluxFlattening(")
        reconstruction = adapter.index("call hy_faceFluxReconstructDirection(")
        solve = adapter.index("call hy_faceFluxSolveDirection(")
        assert flattening < reconstruction < solve
    else:
        raise AssertionError("Unexpected grouping {!r}".format(name))

    if name != "fully_fused":
        assert "if (status/=HY_OK .or. direction<1" in computation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newimpl_source", type=Path)
    parser.add_argument("milhoja_prefix", type=Path)
    args = parser.parse_args()

    contract = ArithmeticHelperContract.load(
        HERE / "newimpl_face_flux.contract.json"
    )
    contract.verify_sources(args.newimpl_source)
    boundaries = KernelBoundaryContract.load(
        HERE / "newimpl_face_flux.boundaries.json",
        HERE / "newimpl_face_flux.contract.json",
    )
    verify_layout_transforms()

    for layout in LAYOUT_CHOICES:
        for grouping_name in boundaries.legal_grouping_names:
            grouping = boundaries.legal_grouping(grouping_name)
            with tempfile.TemporaryDirectory(
                    prefix="newimpl-layout-a-") as first_name, \
                    tempfile.TemporaryDirectory(
                        prefix="newimpl-layout-b-") as second_name:
                first = Path(first_name)
                second = Path(second_name)
                _generate(
                    args.newimpl_source, args.milhoja_prefix, first, 1,
                    layout, grouping_name,
                )
                _generate(
                    args.newimpl_source, args.milhoja_prefix, second, 777,
                    layout, grouping_name,
                )

                actual_files = {
                    path.name for path in first.iterdir() if path.is_file()
                }
                assert actual_files == EXPECTED_FILES
                _verify_specification(first, layout, grouping)
                _verify_layout_sources(first, layout)
                _verify_host_sources(first)
                _verify_grouped_sources(first, grouping)
                _assert_equal_directories(first, second)
                _verify_standalone_generation(
                    args.newimpl_source, first, layout
                )

    print("NewImpl HOSTMEM layout/grouping generation verification passed")


if __name__ == "__main__":
    main()

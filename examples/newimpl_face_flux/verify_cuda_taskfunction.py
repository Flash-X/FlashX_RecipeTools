#!/usr/bin/env python3
"""Verify deterministic CUDA/OpenACC TaskFunction generation."""

import argparse
import filecmp
import json
import os
import subprocess
import sys
import tempfile

from pathlib import Path

from FlashX_RecipeTools import KernelBoundaryContract
from grouping_config import adapter_names
from layout_config import LAYOUT_CHOICES


HERE = Path(__file__).resolve().parent
GENERATOR = HERE / "generate_taskfunction.py"


def generate(source, prefix, destination, seed, layout, grouping):
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = str(seed)
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            str(source),
            str(prefix),
            str(destination),
            "--execution",
            "cuda-openacc",
            "--layout",
            layout,
            "--grouping",
            grouping,
        ],
        check=True,
        env=environment,
    )


def require_equal_directories(first, second):
    comparison = filecmp.dircmp(first, second)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        raise AssertionError("Generated CUDA/OpenACC file sets differ")
    differing = [
        name
        for name in comparison.common_files
        if not filecmp.cmp(first / name, second / name, shallow=False)
    ]
    if differing:
        raise AssertionError(
            "Nondeterministic CUDA/OpenACC files: {}".format(
                ", ".join(differing)
            )
        )


def verify_sources(output, grouping):
    specification = json.loads(
        (output / "newimpl_face_flux.taskfunction.json").read_text()
    )
    task = specification["task_function"]
    assert task["processor"] == "GPU"
    assert task["computation_offloading"] == "OpenACC"
    assert task["subroutine_call_graph"] == list(adapter_names(grouping))
    mapping = json.loads(
        (output / "newimpl_face_flux.mapping.json").read_text()
    )
    assert mapping["execution"] == {
        "name": "cuda-openacc",
        "processor": "GPU",
        "offloading": "OpenACC",
    }

    computation = (output / "newimpl_face_flux_milhoja.F90").read_text()
    adapter = (output / "newimpl_face_flux_adapter_mod.F90").read_text()
    wrapper = (output / "newimpl_face_flux_tf_mod.F90").read_text()
    cpp = (output / "newimpl_face_flux_tf.cxx").read_text()

    assert "type(flux_direction) :: directions(2)" in computation
    assert "allocatable :: directions" not in computation
    assert "allocate(flux_view%directions" not in adapter
    assert "deallocate(flux_view%directions" not in adapter
    assert adapter.count("!$acc routine vector") >= len(adapter_names(grouping))
    assert "!$acc parallel loop gang" in wrapper
    assert "deviceptr(" in wrapper
    assert "MILHOJA_OPENACC_OFFLOADING" in cpp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newimpl_source", type=Path)
    parser.add_argument("milhoja_prefix", type=Path)
    args = parser.parse_args()

    boundaries = KernelBoundaryContract.load(
        HERE / "newimpl_face_flux.boundaries.json",
        HERE / "newimpl_face_flux.contract.json",
    )
    boundaries.arithmetic_contract.verify_sources(args.newimpl_source)

    for layout in LAYOUT_CHOICES:
        for grouping in boundaries.legal_grouping_names:
            with tempfile.TemporaryDirectory(
                prefix="newimpl-cuda-a-"
            ) as first_name, tempfile.TemporaryDirectory(
                prefix="newimpl-cuda-b-"
            ) as second_name:
                first = Path(first_name)
                second = Path(second_name)
                generate(
                    args.newimpl_source,
                    args.milhoja_prefix,
                    first,
                    1,
                    layout,
                    grouping,
                )
                generate(
                    args.newimpl_source,
                    args.milhoja_prefix,
                    second,
                    777,
                    layout,
                    grouping,
                )
                verify_sources(first, grouping)
                require_equal_directories(first, second)
                print("Verified CUDA/OpenACC {} / {}".format(
                    layout, grouping
                ))

    print("NewImpl CUDA/OpenACC generation verification passed")


if __name__ == "__main__":
    main()

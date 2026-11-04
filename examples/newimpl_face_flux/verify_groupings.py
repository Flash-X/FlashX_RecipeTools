#!/usr/bin/env python3
"""Compile and run every legal NewImpl grouping and data layout."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from FlashX_RecipeTools import KernelBoundaryContract
from layout_config import LAYOUT_CHOICES


HERE = Path(__file__).resolve().parent
COMPUTATION_GENERATOR = HERE / "generate_computation.py"
TEST_GENERATOR = HERE / "generate_test.py"


def _run(command, environment=None):
    subprocess.run(command, check=True, env=environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newimpl_source", type=Path)
    parser.add_argument(
        "--fc",
        default=os.environ.get("FC", "gfortran"),
        help="host Fortran compiler (default: FC or gfortran)",
    )
    args = parser.parse_args()

    boundaries = KernelBoundaryContract.load(
        HERE / "newimpl_face_flux.boundaries.json",
        HERE / "newimpl_face_flux.contract.json",
    )
    boundaries.arithmetic_contract.verify_sources(args.newimpl_source)

    with tempfile.TemporaryDirectory(prefix="newimpl-groupings-") as name:
        root = Path(name)
        for layout in LAYOUT_CHOICES:
            for grouping in boundaries.legal_grouping_names:
                build = root / layout / grouping
                build.mkdir(parents=True)
                computation = build / "newimpl_face_flux_milhoja.F90"
                test = build / "test_newimpl_face_flux_milhoja.F90"
                executable = build / "test_newimpl_face_flux_milhoja"
                _run(
                    [
                        sys.executable,
                        str(COMPUTATION_GENERATOR),
                        str(args.newimpl_source),
                        str(computation),
                        "--layout",
                        layout,
                        "--grouping",
                        grouping,
                    ]
                )
                _run(
                    [
                        sys.executable,
                        str(TEST_GENERATOR),
                        str(args.newimpl_source),
                        str(test),
                        "--layout",
                        layout,
                    ]
                )
                _run(
                    [
                        args.fc,
                        "-std=f2008",
                        "-fcheck=all",
                        "-J",
                        str(build),
                        "-I",
                        str(build),
                        str(computation),
                        str(test),
                        "-o",
                        str(executable),
                    ]
                )
                _run([str(executable)])
                print("Verified {} / {}".format(layout, grouping))

    print("All NewImpl layout/grouping scientific tests passed")


if __name__ == "__main__":
    main()

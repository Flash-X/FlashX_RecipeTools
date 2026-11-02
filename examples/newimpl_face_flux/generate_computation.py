#!/usr/bin/env python3
"""Generate the validated NewImpl face-flux computation for Milhoja HOSTMEM."""

import argparse

from pathlib import Path

from FlashX_RecipeTools import ArithmeticHelperContract, ComputationSourceGenerator
from layout_config import LAYOUT_CHOICES, VARIABLE_LAST, layout_binding


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "newimpl_source",
        type=Path,
        help="directory containing the contracted NewImpl arithmetic sources",
    )
    parser.add_argument("output", type=Path, help="generated Fortran source path")
    parser.add_argument(
        "--layout", choices=LAYOUT_CHOICES, default=VARIABLE_LAST,
        help="component ordering for generated field views",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output file",
    )
    args = parser.parse_args()

    contract = ArithmeticHelperContract.load(HERE / "newimpl_face_flux.contract.json")
    generator = ComputationSourceGenerator(contract)
    output = generator.generate(
        args.newimpl_source,
        layout_binding(HERE, args.layout),
        args.output,
        overwrite=args.overwrite,
    )
    print("Generated {} from validated {}".format(output, contract.name))


if __name__ == "__main__":
    main()

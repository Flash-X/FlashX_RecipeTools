#!/usr/bin/env python3
"""Generate a validated grouped NewImpl face-flux computation."""

import argparse

from pathlib import Path

from FlashX_RecipeTools import ComputationSourceGenerator, KernelBoundaryContract
from grouping_config import FULLY_FUSED, grouped_arithmetic_transform
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
    boundaries = KernelBoundaryContract.load(
        HERE / "newimpl_face_flux.boundaries.json",
        HERE / "newimpl_face_flux.contract.json",
    )
    parser.add_argument(
        "--grouping",
        choices=boundaries.legal_grouping_names,
        default=FULLY_FUSED,
        help="validated kernel grouping to lower",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output file",
    )
    args = parser.parse_args()

    contract = boundaries.arithmetic_contract
    generator = ComputationSourceGenerator(contract)
    if args.grouping == FULLY_FUSED:
        output = generator.generate(
            args.newimpl_source,
            layout_binding(HERE, args.layout),
            args.output,
            overwrite=args.overwrite,
        )
    else:
        output = generator.generate_derived(
            args.newimpl_source,
            layout_binding(HERE, args.layout),
            args.output,
            grouped_arithmetic_transform(args.grouping),
            "module",
            "newimpl_hydro",
            overwrite=args.overwrite,
        )
    print("Generated {} from validated {} using {}".format(
        output, contract.name, args.grouping
    ))


if __name__ == "__main__":
    main()

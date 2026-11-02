#!/usr/bin/env python3
"""Validate the NewImpl face-flux contract against a NewImpl source directory."""

import argparse

from pathlib import Path

from FlashX_RecipeTools import ArithmeticHelperContract


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "newimpl_source",
        type=Path,
        help="directory containing hy_getFaceFlux.F90-mc and hydro_helpers.ini",
    )
    args = parser.parse_args()

    contract = ArithmeticHelperContract.load(HERE / "newimpl_face_flux.contract.json")
    contract.verify_sources(args.newimpl_source)
    print("Validated {} against {}".format(contract.name, args.newimpl_source.resolve()))


if __name__ == "__main__":
    main()

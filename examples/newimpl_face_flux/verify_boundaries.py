#!/usr/bin/env python3
"""Verify the Step 7 NewImpl face-flux boundary declaration."""

import argparse
from pathlib import Path

from FlashX_RecipeTools import KernelBoundaryContract


HERE = Path(__file__).resolve().parent
ARITHMETIC_CONTRACT = HERE / "newimpl_face_flux.contract.json"
BOUNDARY_CONTRACT = HERE / "newimpl_face_flux.boundaries.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newimpl_source", type=Path)
    args = parser.parse_args()

    contract = KernelBoundaryContract.load(BOUNDARY_CONTRACT, ARITHMETIC_CONTRACT)
    contract.arithmetic_contract.verify_sources(args.newimpl_source)

    print("Validated {} against checksummed NewImpl sources".format(contract.name))
    print("Legal groupings: {}".format(", ".join(contract.legal_grouping_names)))


if __name__ == "__main__":
    main()

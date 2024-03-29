import FlashX_RecipeTools as flashx

import json
from pathlib import Path

CWD = Path(__file__).parent.absolute()
REF_FILE_PATH = CWD / Path("ref/Hydro_interface_ref.json")


def test_generate_op_spec():

    intf_file = CWD / Path("Hydro_interface.F90")

    op_spec_name = "__" + intf_file.stem
    op_spec_path = flashx.generate_op_spec(op_spec_name, intf_file, debug=True, call_cpp=True)

    with open(op_spec_path, 'r') as fptr:
        generated_op_spec = json.load(fptr)

    with open(REF_FILE_PATH, 'r') as fptr:
        ref_op_spec = json.load(fptr)

    assert generated_op_spec == ref_op_spec


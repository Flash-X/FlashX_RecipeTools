import copy
import hashlib
import json
import textwrap

from pathlib import Path

import pytest

from FlashX_RecipeTools import (
    ArithmeticHelperContract,
    ArithmeticHelperContractError,
    ComputationSourceGenerationError,
    ComputationSourceGenerator,
)


HELPERS = """\
first
args=input,work
scope=block
definition=
  work=input

second
args=work,output
scope=block
definition=
  output=work
"""

ARITHMETIC = """\
subroutine face_flux(input,output)
  implicit none
end subroutine face_flux
"""

EXPANDER = "# deterministic test expander\n"

GENERATION_ARITHMETIC = """\
subroutine face_flux(input,output)
  implicit none
  @first(input,work)@
  @second(work,output)@
end subroutine face_flux
"""

GENERATION_EXPANDER = textwrap.dedent(
    """\
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--definitions", nargs="+")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--reject-duplicates", action="store_true")
    args = parser.parse_args()
    source = Path(args.input).read_text(encoding="utf-8")
    source = source.replace("@first(input,work)@", "work=input")
    source = source.replace("@second(work,output)@", "output=work")
    Path(args.output).write_text(source, encoding="utf-8")
    """
)

LAYOUT_BINDING = """\
cell_ref
args=data,var,block,i,j,k
definition=data(var,i,j,k,block)
"""


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def valid_contract():
    return {
        "format": {"name": "FlashX-ArithmeticHelper-Contract", "version": "1.0.0"},
        "name": "test_face_flux",
        "sources": {
            "arithmetic": {"path": "arithmetic.F90-mc", "sha256": digest(ARITHMETIC)},
            "helpers": {"path": "helpers.ini", "sha256": digest(HELPERS)},
            "expander": {"path": "expander.py", "sha256": digest(EXPANDER)},
        },
        "entrypoint": "face_flux",
        "layout_symbols": ["cell_ref"],
        "require_complete_helper_inventory": True,
        "helper_interfaces": {"first": ["input", "work"], "second": ["work", "output"]},
        "data_objects": {
            "input": {
                "kind": "field",
                "role": "input",
                "access": [{"mode": "read", "region": "cells"}],
            },
            "work": {
                "kind": "scratch",
                "role": "intermediate",
                "lifetime": "stage",
                "producer": "prepare",
                "consumers": ["finish"],
                "access": [
                    {"mode": "write", "region": "cells"},
                    {"mode": "read", "region": "cells"},
                ],
            },
            "output": {
                "kind": "field",
                "role": "output",
                "access": [{"mode": "write", "region": "cells"}],
            },
            "maximum": {
                "kind": "scalar",
                "role": "reduction",
                "access": [{"mode": "reduction", "region": "cells"}],
            },
            "status": {
                "kind": "scalar",
                "role": "status",
                "access": [{"mode": "write", "region": "invocation"}],
            },
        },
        "operations": [
            {
                "name": "prepare",
                "domain": "cells",
                "helpers": ["first"],
                "reads": ["input"],
                "writes": ["work", "status"],
                "depends_on": [],
            },
            {
                "name": "finish",
                "domain": "cells",
                "helpers": ["second"],
                "reads": ["work"],
                "writes": ["output", "maximum", "status"],
                "depends_on": ["prepare"],
            },
        ],
        "synchronization": [
            {
                "after": "prepare",
                "before": "finish",
                "relation": "direct_dependency",
                "scope": "stage",
                "reason": "work dependency",
            }
        ],
        "reductions": [{"target": "maximum", "operator": "max", "identity": 0.0, "operation": "finish"}],
        "failure_semantics": {
            "status": "status",
            "success_value": "OK",
            "partial_writes": True,
            "commit_partial_results": False,
        },
        "baseline_grouping": {
            "task_function": "one_stage",
            "kernel_grouping": "fixed",
            "allow_fusion": False,
            "allow_splitting": False,
        },
    }


@pytest.fixture
def source_root(tmp_path):
    (tmp_path / "arithmetic.F90-mc").write_text(ARITHMETIC, encoding="utf-8")
    (tmp_path / "helpers.ini").write_text(HELPERS, encoding="utf-8")
    (tmp_path / "expander.py").write_text(EXPANDER, encoding="utf-8")
    return tmp_path


def load_contract(tmp_path, data):
    filename = tmp_path / "contract.json"
    filename.write_text(json.dumps(data), encoding="utf-8")
    return ArithmeticHelperContract.load(filename)


def test_valid_contract_and_sources(tmp_path, source_root):
    contract = load_contract(tmp_path, valid_contract())
    paths = contract.verify_sources(source_root)
    assert contract.name == "test_face_flux"
    assert paths["helpers"] == (source_root / "helpers.ini").resolve()


def test_helper_argument_mismatch_is_rejected(tmp_path, source_root):
    data = valid_contract()
    data["helper_interfaces"]["first"] = ["work", "input"]
    contract = load_contract(tmp_path, data)
    with pytest.raises(ArithmeticHelperContractError, match="arguments differ"):
        contract.verify_sources(source_root)


def test_missing_helper_is_rejected(tmp_path, source_root):
    data = valid_contract()
    data["helper_interfaces"]["missing"] = []
    contract = load_contract(tmp_path, data)
    with pytest.raises(ArithmeticHelperContractError, match="is not defined"):
        contract.verify_sources(source_root)


@pytest.mark.parametrize("role", ["arithmetic", "helpers", "expander"])
def test_checksum_mismatch_is_rejected(tmp_path, source_root, role):
    data = valid_contract()
    data["sources"][role]["sha256"] = "0" * 64
    contract = load_contract(tmp_path, data)
    with pytest.raises(ArithmeticHelperContractError, match="checksum mismatch"):
        contract.verify_sources(source_root)


def test_undeclared_data_reference_is_rejected():
    data = valid_contract()
    data["operations"][0]["reads"].append("unknown")
    with pytest.raises(ArithmeticHelperContractError, match="undeclared data object"):
        ArithmeticHelperContract(data)


def test_dependency_cycle_is_rejected():
    data = valid_contract()
    data["operations"][0]["depends_on"] = ["finish"]
    with pytest.raises(ArithmeticHelperContractError, match="contain a cycle"):
        ArithmeticHelperContract(data)


def test_invalid_scratch_producer_is_rejected():
    data = valid_contract()
    data["data_objects"]["work"]["producer"] = "finish"
    with pytest.raises(ArithmeticHelperContractError, match="does not write"):
        ArithmeticHelperContract(data)


def test_barrier_must_match_dependency():
    data = valid_contract()
    data["synchronization"][0]["after"] = "finish"
    with pytest.raises(ArithmeticHelperContractError, match="direct operation dependency"):
        ArithmeticHelperContract(data)


def test_contract_data_is_not_mutated():
    data = valid_contract()
    original = copy.deepcopy(data)
    ArithmeticHelperContract(data)
    assert data == original


@pytest.fixture
def generation_inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "arithmetic.F90-mc").write_text(GENERATION_ARITHMETIC, encoding="utf-8")
    (source / "helpers.ini").write_text(HELPERS, encoding="utf-8")
    (source / "expander.py").write_text(GENERATION_EXPANDER, encoding="utf-8")
    binding = tmp_path / "layout.ini"
    binding.write_text(LAYOUT_BINDING, encoding="utf-8")

    data = valid_contract()
    data["sources"]["arithmetic"]["sha256"] = digest(GENERATION_ARITHMETIC)
    data["sources"]["expander"]["sha256"] = digest(GENERATION_EXPANDER)
    contract = load_contract(tmp_path, data)
    return source, binding, contract


def test_computation_generation_is_deterministic_and_preserves_order(tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    generator = ComputationSourceGenerator(contract)
    first = generator.generate(source, binding, tmp_path / "first.F90")
    second = generator.generate(source, binding, tmp_path / "second.F90")

    first_text = first.read_text(encoding="utf-8")
    assert first_text == second.read_text(encoding="utf-8")
    assert first_text.index("work=input") < first_text.index("output=work")
    assert "@first" not in first_text
    assert "@second" not in first_text


def test_computation_generation_refuses_to_overwrite(tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    output = tmp_path / "generated.F90"
    output.write_text("user-owned\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        ComputationSourceGenerator(contract).generate(source, binding, output)
    assert output.read_text(encoding="utf-8") == "user-owned\n"


def test_computation_generation_rejects_incomplete_binding(tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    binding.write_text("other\ndefinition=value\n", encoding="utf-8")

    with pytest.raises(ComputationSourceGenerationError, match="omits required macros"):
        ComputationSourceGenerator(contract).generate(source, binding, tmp_path / "generated.F90")


def test_computation_generation_rejects_unresolved_macros(tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    arithmetic = GENERATION_ARITHMETIC.replace(
        "end subroutine face_flux", "  @unresolved@\nend subroutine face_flux"
    )
    (source / "arithmetic.F90-mc").write_text(arithmetic, encoding="utf-8")
    data = copy.deepcopy(contract.data)
    data["sources"]["arithmetic"]["sha256"] = digest(arithmetic)
    contract = load_contract(tmp_path, data)
    output = tmp_path / "generated.F90"

    with pytest.raises(ComputationSourceGenerationError, match="unresolved macro"):
        ComputationSourceGenerator(contract).generate(source, binding, output)
    assert not output.exists()


def test_computation_generation_rejects_unresolved_placeholders(
        tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    arithmetic = GENERATION_ARITHMETIC.replace(
        "end subroutine face_flux",
        "  output=${macro_scope_1_arg_data}\nend subroutine face_flux",
    )
    (source / "arithmetic.F90-mc").write_text(arithmetic, encoding="utf-8")
    data = copy.deepcopy(contract.data)
    data["sources"]["arithmetic"]["sha256"] = digest(arithmetic)
    contract = load_contract(tmp_path, data)
    output = tmp_path / "generated.F90"

    with pytest.raises(
            ComputationSourceGenerationError, match="unresolved placeholder"):
        ComputationSourceGenerator(contract).generate(source, binding, output)
    assert not output.exists()


def test_auxiliary_generation_checks_source_hash(tmp_path, generation_inputs):
    source, binding, contract = generation_inputs
    test_source = "program test_hydro\nend program test_hydro\n"
    (source / "test_hydro.F90-mc").write_text(test_source, encoding="utf-8")
    generator = ComputationSourceGenerator(contract)

    output = generator.generate_auxiliary(
        source,
        "test_hydro.F90-mc",
        digest(test_source),
        binding,
        tmp_path / "test_hydro.F90",
        "program",
        "test_hydro",
    )
    assert "program test_hydro" in output.read_text(encoding="utf-8")

    with pytest.raises(ComputationSourceGenerationError, match="checksum mismatch"):
        generator.generate_auxiliary(
            source,
            "test_hydro.F90-mc",
            "0" * 64,
            binding,
            tmp_path / "bad_test_hydro.F90",
            "program",
            "test_hydro",
        )

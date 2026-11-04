import copy
import hashlib
import json

import pytest

from FlashX_RecipeTools import (
    ArithmeticHelperContract,
    KernelBoundaryContract,
    KernelBoundaryContractError,
)


def arithmetic_data():
    return {
        "format": {"name": "FlashX-ArithmeticHelper-Contract", "version": "1.0.0"},
        "name": "test_stage",
        "sources": {
            role: {"path": "{}.txt".format(role), "sha256": "0" * 64}
            for role in ("arithmetic", "helpers", "expander")
        },
        "entrypoint": "test_stage",
        "layout_symbols": ["cell_ref"],
        "helper_interfaces": {"prepare_helper": [], "finish_helper": []},
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
                "helpers": ["prepare_helper"],
                "reads": ["input"],
                "writes": ["work", "status"],
                "depends_on": [],
            },
            {
                "name": "finish",
                "domain": "cells",
                "helpers": ["finish_helper"],
                "reads": ["work"],
                "writes": ["output", "status"],
                "depends_on": ["prepare"],
            },
        ],
        "synchronization": [
            {
                "after": "prepare",
                "before": "finish",
                "relation": "direct_dependency",
                "scope": "stage",
                "reason": "work must be complete",
            }
        ],
        "reductions": [],
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


def boundary_data():
    return {
        "format": {"name": "FlashX-KernelBoundary-Contract", "version": "1.0.0"},
        "name": "test_boundaries",
        "arithmetic_contract": {"name": "test_stage", "sha256": "0" * 64},
        "operation_order": ["prepare", "finish"],
        "operation_domains": {"prepare": "cells", "finish": "cells"},
        "scratch_lifetimes": {"work": "stage"},
        "reference_schedule": "prepare then finish",
        "constraints": {
            "preserve_order": {
                "description": "Preserve operation order.",
                "requirement": "Do not reorder operations.",
            }
        },
        "boundaries": [
            {
                "name": "after_prepare",
                "after": "prepare",
                "before": "finish",
                "relation": "direct_dependency",
                "scope": "stage",
                "live_intermediates": ["work"],
                "control_state": ["status"],
                "materialize": ["work", "status"],
                "required_synchronization": "same_kernel_or_kernel_completion",
                "constraints": ["preserve_order"],
            }
        ],
        "legal_groupings": [
            {
                "name": "fused",
                "kernel_groups": [["prepare", "finish"]],
                "cuts": [],
                "required_boundaries": [],
                "schedule": "prepare then finish",
                "constraints": ["preserve_order"],
            },
            {
                "name": "split",
                "kernel_groups": [["prepare"], ["finish"]],
                "cuts": ["after_prepare"],
                "required_boundaries": [],
                "schedule": "prepare then finish",
                "constraints": ["preserve_order"],
            },
        ],
        "prohibited_transformations": [
            {
                "name": "reverse",
                "reason": "The consumer cannot precede its producer.",
                "violates": ["preserve_order"],
            }
        ],
    }


def make_contract(data=None, arithmetic=None):
    arithmetic = ArithmeticHelperContract(
        arithmetic_data() if arithmetic is None else arithmetic
    )
    return KernelBoundaryContract(boundary_data() if data is None else data, arithmetic)


def test_valid_boundary_contract_declares_fused_and_split_groupings():
    contract = make_contract()
    assert contract.name == "test_boundaries"
    assert contract.legal_grouping_names == ("fused", "split")
    assert contract.legal_grouping("split")["kernel_groups"] == [
        ["prepare"],
        ["finish"],
    ]


def test_unknown_legal_grouping_is_rejected():
    with pytest.raises(KernelBoundaryContractError, match="Unknown legal grouping"):
        make_contract().legal_grouping("unknown")


def test_operation_order_must_match_arithmetic_contract():
    data = boundary_data()
    data["operation_order"].reverse()
    with pytest.raises(KernelBoundaryContractError, match="operation_order must exactly match"):
        make_contract(data)


def test_operation_domains_must_match_arithmetic_contract():
    data = boundary_data()
    data["operation_domains"]["finish"] = "faces"
    with pytest.raises(KernelBoundaryContractError, match="operation_domains"):
        make_contract(data)


def test_scratch_lifetimes_must_match_arithmetic_contract():
    data = boundary_data()
    data["scratch_lifetimes"]["work"] = "one_iteration"
    with pytest.raises(KernelBoundaryContractError, match="scratch_lifetimes"):
        make_contract(data)


def test_boundary_must_match_arithmetic_synchronization():
    data = boundary_data()
    data["boundaries"][0]["scope"] = "direction"
    with pytest.raises(KernelBoundaryContractError, match="synchronization edge"):
        make_contract(data)


def test_live_intermediate_must_flow_from_producer_to_consumer():
    data = boundary_data()
    data["boundaries"][0]["live_intermediates"] = ["input"]
    data["boundaries"][0]["materialize"] = ["input", "status"]
    with pytest.raises(KernelBoundaryContractError, match="is not written"):
        make_contract(data)


def test_materialized_value_must_be_live():
    data = boundary_data()
    data["boundaries"][0]["materialize"].append("output")
    with pytest.raises(KernelBoundaryContractError, match="must be live"):
        make_contract(data)


def test_kernel_groups_cannot_reorder_operations():
    data = boundary_data()
    data["legal_groupings"][0]["kernel_groups"] = [["finish", "prepare"]]
    with pytest.raises(KernelBoundaryContractError, match="without reordering"):
        make_contract(data)


def test_grouping_cuts_must_match_group_transitions():
    data = boundary_data()
    data["legal_groupings"][1]["cuts"] = []
    with pytest.raises(KernelBoundaryContractError, match="cuts must match"):
        make_contract(data)


def test_every_grouping_must_preserve_every_constraint():
    data = boundary_data()
    data["constraints"]["preserve_failure"] = {
        "description": "Preserve failure behavior.",
        "requirement": "Stop after failure.",
    }
    with pytest.raises(KernelBoundaryContractError, match="every global constraint"):
        make_contract(data)


def test_every_grouping_must_retain_next_iteration_boundaries():
    arithmetic = arithmetic_data()
    arithmetic["synchronization"].append(
        {
            "after": "finish",
            "before": "prepare",
            "relation": "next_iteration",
            "scope": "iteration_transition",
            "reason": "one iteration must finish before the next starts",
        }
    )
    data = boundary_data()
    data["boundaries"].append(
        {
            "name": "iteration_transition",
            "after": "finish",
            "before": "prepare",
            "relation": "next_iteration",
            "scope": "iteration_transition",
            "live_intermediates": ["output"],
            "control_state": ["status"],
            "materialize": ["output", "status"],
            "required_synchronization": "kernel_completion",
            "constraints": ["preserve_order"],
        }
    )
    with pytest.raises(
        KernelBoundaryContractError, match="must retain iteration boundaries"
    ):
        make_contract(data, arithmetic)


def test_contract_data_is_not_mutated():
    data = boundary_data()
    original = copy.deepcopy(data)
    make_contract(data)
    assert data == original


def test_arithmetic_contract_checksum_is_enforced(tmp_path):
    arithmetic_path = tmp_path / "arithmetic.json"
    arithmetic_path.write_text(json.dumps(arithmetic_data()), encoding="utf-8")
    data = boundary_data()
    data["arithmetic_contract"]["sha256"] = hashlib.sha256(
        arithmetic_path.read_bytes()
    ).hexdigest()
    boundary_path = tmp_path / "boundaries.json"
    boundary_path.write_text(json.dumps(data), encoding="utf-8")

    KernelBoundaryContract.load(boundary_path, arithmetic_path)
    arithmetic_path.write_text(
        json.dumps(arithmetic_data(), indent=2), encoding="utf-8"
    )
    with pytest.raises(KernelBoundaryContractError, match="checksum mismatch"):
        KernelBoundaryContract.load(boundary_path, arithmetic_path)

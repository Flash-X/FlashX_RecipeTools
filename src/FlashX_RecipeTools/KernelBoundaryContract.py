"""Validation for declared legal kernel boundaries.

The boundary contract is application-supplied metadata layered on a
checksummed :class:`ArithmeticHelperContract`.  It describes a finite set of
legal cuts without deriving dependencies from arbitrary Fortran or creating a
compiler intermediate representation.
"""

import hashlib
import json
import re
from pathlib import Path

from .ArithmeticHelperContract import ArithmeticHelperContract


class KernelBoundaryContractError(ValueError):
    """Raised when a kernel-boundary contract is invalid."""


class KernelBoundaryContract:
    """Load and validate legal cuts against an arithmetic-helper contract."""

    FORMAT_NAME = "FlashX-KernelBoundary-Contract"
    FORMAT_VERSION = "1.0.0"
    _IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
    _SHA256 = re.compile(r"^[0-9a-f]{64}$")
    _SYNCHRONIZATION = {
        "kernel_completion",
        "same_kernel_or_kernel_completion",
    }

    def __init__(self, data, arithmetic_contract, filename=None):
        if not isinstance(arithmetic_contract, ArithmeticHelperContract):
            raise TypeError("arithmetic_contract must be an ArithmeticHelperContract")
        self.data = data
        self.arithmetic_contract = arithmetic_contract
        self.filename = Path(filename).resolve() if filename is not None else None
        self.validate()

    @classmethod
    def load(cls, filename, arithmetic_contract_filename):
        """Load both contracts and verify the boundary-to-arithmetic binding."""
        boundary_path = Path(filename)
        arithmetic_path = Path(arithmetic_contract_filename)
        try:
            with boundary_path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise KernelBoundaryContractError(
                "Unable to load kernel-boundary contract {!s}: {}".format(
                    boundary_path, exc
                )
            ) from exc
        arithmetic_contract = ArithmeticHelperContract.load(arithmetic_path)
        result = cls(data, arithmetic_contract, boundary_path)
        result._verify_arithmetic_checksum(arithmetic_path)
        return result

    @property
    def name(self):
        return self.data["name"]

    @property
    def legal_grouping_names(self):
        return tuple(grouping["name"] for grouping in self.data["legal_groupings"])

    def validate(self):
        root = self._mapping(self.data, "boundary contract")
        self._check_keys(
            root,
            "boundary contract",
            required={
                "format",
                "name",
                "arithmetic_contract",
                "operation_order",
                "operation_domains",
                "scratch_lifetimes",
                "reference_schedule",
                "constraints",
                "boundaries",
                "legal_groupings",
                "prohibited_transformations",
            },
        )

        fmt = self._mapping(root["format"], "format")
        self._check_keys(fmt, "format", required={"name", "version"})
        if fmt["name"] != self.FORMAT_NAME or fmt["version"] != self.FORMAT_VERSION:
            self._error(
                "format must be {} version {}".format(
                    self.FORMAT_NAME, self.FORMAT_VERSION
                )
            )

        self._identifier(root["name"], "name")
        self._validate_arithmetic_reference(root["arithmetic_contract"])

        operations = self.arithmetic_contract.data["operations"]
        expected_order = [operation["name"] for operation in operations]
        operation_order = self._identifier_list(
            root["operation_order"], "operation_order", nonempty=True
        )
        if operation_order != expected_order:
            self._error(
                "operation_order must exactly match the arithmetic contract: {}".format(
                    ", ".join(expected_order)
                )
            )
        self._validate_operation_domains(root["operation_domains"], operations)
        self._validate_scratch_lifetimes(root["scratch_lifetimes"])
        if not isinstance(root["reference_schedule"], str) or not root["reference_schedule"]:
            self._error("reference_schedule must be a nonempty string")

        constraints = self._validate_constraints(root["constraints"])
        boundaries = self._validate_boundaries(root["boundaries"], constraints)
        self._validate_groupings(
            root["legal_groupings"], operation_order, boundaries, constraints
        )
        self._validate_prohibited(
            root["prohibited_transformations"], constraints
        )

    def _validate_arithmetic_reference(self, reference):
        reference = self._mapping(reference, "arithmetic_contract")
        self._check_keys(reference, "arithmetic_contract", required={"name", "sha256"})
        if reference["name"] != self.arithmetic_contract.name:
            self._error(
                "arithmetic_contract.name {!r} does not match {!r}".format(
                    reference["name"], self.arithmetic_contract.name
                )
            )
        if not isinstance(reference["sha256"], str) or self._SHA256.fullmatch(
            reference["sha256"]
        ) is None:
            self._error("arithmetic_contract.sha256 must be a lowercase SHA-256 digest")

    def _validate_operation_domains(self, domains, operations):
        domains = self._mapping(domains, "operation_domains", nonempty=True)
        expected = {operation["name"]: operation["domain"] for operation in operations}
        if domains != expected:
            self._error("operation_domains must exactly match the arithmetic contract")

    def _validate_scratch_lifetimes(self, lifetimes):
        lifetimes = self._mapping(lifetimes, "scratch_lifetimes")
        expected = {
            name: specification["lifetime"]
            for name, specification in self.arithmetic_contract.data[
                "data_objects"
            ].items()
            if specification["kind"] == "scratch"
        }
        if lifetimes != expected:
            self._error("scratch_lifetimes must exactly match the arithmetic contract")

    def _verify_arithmetic_checksum(self, arithmetic_path):
        try:
            actual = hashlib.sha256(arithmetic_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise KernelBoundaryContractError(
                "Unable to read arithmetic contract {!s}: {}".format(
                    arithmetic_path, exc
                )
            ) from exc
        expected = self.data["arithmetic_contract"]["sha256"]
        if actual != expected:
            self._error(
                "arithmetic contract checksum mismatch for {!s}: expected {}, found {}".format(
                    arithmetic_path, expected, actual
                )
            )

    def _validate_constraints(self, constraints):
        constraints = self._mapping(constraints, "constraints", nonempty=True)
        for name, specification in constraints.items():
            self._identifier(name, "constraints key")
            label = "constraints.{}".format(name)
            specification = self._mapping(specification, label)
            self._check_keys(
                specification,
                label,
                required={"description", "requirement"},
            )
            for key in ("description", "requirement"):
                if not isinstance(specification[key], str) or not specification[key]:
                    self._error("{}.{} must be a nonempty string".format(label, key))
        return constraints

    def _validate_boundaries(self, boundaries, constraints):
        boundaries = self._list(boundaries, "boundaries", nonempty=True)
        operations = {
            operation["name"]: operation
            for operation in self.arithmetic_contract.data["operations"]
        }
        data_objects = self.arithmetic_contract.data["data_objects"]
        synchronization = self.arithmetic_contract.data["synchronization"]
        by_name = {}
        for index, boundary in enumerate(boundaries):
            label = "boundaries[{}]".format(index)
            boundary = self._mapping(boundary, label)
            self._check_keys(
                boundary,
                label,
                required={
                    "name",
                    "after",
                    "before",
                    "relation",
                    "scope",
                    "live_intermediates",
                    "control_state",
                    "materialize",
                    "required_synchronization",
                    "constraints",
                },
            )
            name = boundary["name"]
            self._identifier(name, "{}.name".format(label))
            if name in by_name:
                self._error("duplicate boundary {!r}".format(name))
            by_name[name] = boundary

            after = boundary["after"]
            before = boundary["before"]
            if after not in operations or before not in operations:
                self._error("{} references an unknown operation".format(label))
            matching_edges = [
                edge
                for edge in synchronization
                if edge["after"] == after
                and edge["before"] == before
                and edge["relation"] == boundary["relation"]
                and edge["scope"] == boundary["scope"]
            ]
            if len(matching_edges) != 1:
                self._error(
                    "{} must match exactly one arithmetic synchronization edge".format(
                        label
                    )
                )

            live = self._data_list(
                boundary["live_intermediates"], data_objects,
                "{}.live_intermediates".format(label),
            )
            control = self._data_list(
                boundary["control_state"], data_objects,
                "{}.control_state".format(label),
            )
            materialize = self._data_list(
                boundary["materialize"], data_objects,
                "{}.materialize".format(label),
            )
            if not set(materialize).issubset(set(live) | set(control)):
                self._error("{}.materialize must be live at the boundary".format(label))
            if boundary["relation"] == "direct_dependency":
                for value in live:
                    if value not in operations[after]["writes"]:
                        self._error(
                            "{} live intermediate {!r} is not written by {!r}".format(
                                label, value, after
                            )
                        )
                    if value not in operations[before]["reads"]:
                        self._error(
                            "{} live intermediate {!r} is not read by {!r}".format(
                                label, value, before
                            )
                        )

            if boundary["required_synchronization"] not in self._SYNCHRONIZATION:
                self._error("{}.required_synchronization is unsupported".format(label))
            self._constraint_list(
                boundary["constraints"], constraints, "{}.constraints".format(label)
            )
        return by_name

    def _validate_groupings(self, groupings, operation_order, boundaries, constraints):
        groupings = self._list(groupings, "legal_groupings", nonempty=True)
        if len(groupings) < 2:
            self._error("legal_groupings must declare at least two alternatives")
        iteration_boundaries = {
            name
            for name, boundary in boundaries.items()
            if boundary["relation"] == "next_iteration"
        }
        names = set()
        for index, grouping in enumerate(groupings):
            label = "legal_groupings[{}]".format(index)
            grouping = self._mapping(grouping, label)
            self._check_keys(
                grouping,
                label,
                required={
                    "name",
                    "kernel_groups",
                    "cuts",
                    "required_boundaries",
                    "schedule",
                    "constraints",
                },
            )
            name = grouping["name"]
            self._identifier(name, "{}.name".format(label))
            if name in names:
                self._error("duplicate legal grouping {!r}".format(name))
            names.add(name)

            kernel_groups = self._list(
                grouping["kernel_groups"], "{}.kernel_groups".format(label), nonempty=True
            )
            normalized = []
            for group_index, group in enumerate(kernel_groups):
                normalized.append(
                    self._identifier_list(
                        group,
                        "{}.kernel_groups[{}]".format(label, group_index),
                        nonempty=True,
                    )
                )
            flattened = [operation for group in normalized for operation in group]
            if flattened != operation_order:
                self._error(
                    "{}.kernel_groups must partition operation_order without reordering".format(
                        label
                    )
                )

            cuts = self._boundary_list(
                grouping["cuts"], boundaries, "{}.cuts".format(label)
            )
            expected_cuts = []
            for left, right in zip(normalized, normalized[1:]):
                matches = [
                    boundary_name
                    for boundary_name, boundary in boundaries.items()
                    if boundary["after"] == left[-1]
                    and boundary["before"] == right[0]
                    and boundary["relation"] == "direct_dependency"
                ]
                if len(matches) != 1:
                    self._error(
                        "{} has no unique declared cut between {!r} and {!r}".format(
                            label, left[-1], right[0]
                        )
                    )
                expected_cuts.append(matches[0])
            if cuts != expected_cuts:
                self._error(
                    "{}.cuts must match kernel-group transitions: {}".format(
                        label, ", ".join(expected_cuts)
                    )
                )

            required_boundaries = self._boundary_list(
                grouping["required_boundaries"],
                boundaries,
                "{}.required_boundaries".format(label),
            )
            missing_iteration_boundaries = iteration_boundaries - set(
                required_boundaries
            )
            if missing_iteration_boundaries:
                self._error(
                    "{}.required_boundaries must retain iteration boundaries: {}".format(
                        label, ", ".join(sorted(missing_iteration_boundaries))
                    )
                )
            if grouping["schedule"] != self.data["reference_schedule"]:
                self._error("{}.schedule must preserve reference_schedule".format(label))
            grouping_constraints = self._constraint_list(
                grouping["constraints"], constraints, "{}.constraints".format(label)
            )
            if set(grouping_constraints) != set(constraints):
                self._error("{}.constraints must preserve every global constraint".format(label))

    def _validate_prohibited(self, transformations, constraints):
        transformations = self._list(
            transformations, "prohibited_transformations", nonempty=True
        )
        names = set()
        for index, transformation in enumerate(transformations):
            label = "prohibited_transformations[{}]".format(index)
            transformation = self._mapping(transformation, label)
            self._check_keys(
                transformation,
                label,
                required={"name", "reason", "violates"},
            )
            name = transformation["name"]
            self._identifier(name, "{}.name".format(label))
            if name in names:
                self._error("duplicate prohibited transformation {!r}".format(name))
            names.add(name)
            if not isinstance(transformation["reason"], str) or not transformation["reason"]:
                self._error("{}.reason must be a nonempty string".format(label))
            self._constraint_list(
                transformation["violates"], constraints, "{}.violates".format(label)
            )

    def _data_list(self, values, objects, label):
        values = self._identifier_list(values, label)
        for value in values:
            if value not in objects:
                self._error("{} references undeclared data object {!r}".format(label, value))
        return values

    def _constraint_list(self, values, constraints, label):
        values = self._identifier_list(values, label, nonempty=True)
        for value in values:
            if value not in constraints:
                self._error("{} references undeclared constraint {!r}".format(label, value))
        return values

    def _boundary_list(self, values, boundaries, label):
        values = self._identifier_list(values, label)
        for value in values:
            if value not in boundaries:
                self._error("{} references undeclared boundary {!r}".format(label, value))
        return values

    def _identifier_list(self, values, label, nonempty=False):
        values = self._list(values, label, nonempty=nonempty)
        for index, value in enumerate(values):
            self._identifier(value, "{}[{}]".format(label, index))
        if len(values) != len(set(values)):
            self._error("{} contains duplicates".format(label))
        return values

    def _identifier(self, value, label):
        if not isinstance(value, str) or self._IDENTIFIER.fullmatch(value) is None:
            self._error("{} must be an identifier".format(label))

    def _mapping(self, value, label, nonempty=False):
        if not isinstance(value, dict) or (nonempty and not value):
            self._error(
                "{} must be {}mapping".format(
                    label, "a nonempty " if nonempty else "a "
                )
            )
        return value

    def _list(self, value, label, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            self._error(
                "{} must be {}list".format(
                    label, "a nonempty " if nonempty else "a "
                )
            )
        return value

    def _check_keys(self, mapping, label, required):
        missing = required - set(mapping)
        extra = set(mapping) - required
        if missing:
            self._error("{} is missing keys: {}".format(label, ", ".join(sorted(missing))))
        if extra:
            self._error("{} has unknown keys: {}".format(label, ", ".join(sorted(extra))))

    @staticmethod
    def _error(message):
        raise KernelBoundaryContractError(message)

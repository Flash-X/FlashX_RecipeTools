"""Validation for application-owned arithmetic-helper contracts.

The contract is deliberately descriptive metadata.  It records application
assertions needed by RecipeTools without converting the arithmetic into a
compiler intermediate representation.
"""

import hashlib
import json
import re

from pathlib import Path


class ArithmeticHelperContractError(ValueError):
    """Raised when an arithmetic-helper contract is invalid."""


class ArithmeticHelperContract:
    """Load and validate a versioned arithmetic-helper contract."""

    FORMAT_NAME = "FlashX-ArithmeticHelper-Contract"
    FORMAT_VERSION = "1.0.0"
    _SOURCE_ROLES = {"arithmetic", "helpers", "expander"}
    _ACCESS_MODES = {"read", "write", "read_write", "reduction", "diagnostic"}
    _REDUCTIONS = {"max", "min", "sum", "product", "logical_and", "logical_or"}
    _IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
    _SHA256 = re.compile(r"^[0-9a-f]{64}$")

    def __init__(self, data, filename=None):
        self.data = data
        self.filename = Path(filename).resolve() if filename is not None else None
        self.validate()

    @classmethod
    def load(cls, filename):
        """Load *filename* as JSON and validate its metadata structure."""
        path = Path(filename)
        try:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise ArithmeticHelperContractError(
                "Unable to load arithmetic-helper contract {!s}: {}".format(path, exc)
            ) from exc
        return cls(data, path)

    @property
    def name(self):
        return self.data["name"]

    def validate(self):
        """Validate all metadata that does not require reading source files."""
        root = self._mapping(self.data, "contract")
        self._check_keys(
            root,
            "contract",
            required={
                "format",
                "name",
                "sources",
                "entrypoint",
                "layout_symbols",
                "helper_interfaces",
                "data_objects",
                "operations",
                "synchronization",
                "reductions",
                "failure_semantics",
                "baseline_grouping",
            },
            optional={"require_complete_helper_inventory"},
        )

        fmt = self._mapping(root["format"], "format")
        self._check_keys(fmt, "format", required={"name", "version"})
        if fmt["name"] != self.FORMAT_NAME or fmt["version"] != self.FORMAT_VERSION:
            self._error(
                "format must be {} version {}".format(self.FORMAT_NAME, self.FORMAT_VERSION)
            )

        self._identifier(root["name"], "name")
        self._validate_sources(root["sources"])
        self._identifier(root["entrypoint"], "entrypoint")

        symbols = self._list(root["layout_symbols"], "layout_symbols", nonempty=True)
        for index, symbol in enumerate(symbols):
            self._identifier(symbol, "layout_symbols[{}]".format(index))
        if len(symbols) != len(set(symbols)):
            self._error("layout_symbols contains duplicates")

        self._validate_helper_interfaces(root["helper_interfaces"])
        self._validate_data_objects(root["data_objects"])
        operations = self._validate_operations(root["operations"])
        self._validate_scratch_flow(root["data_objects"], operations)
        self._validate_synchronization(root["synchronization"], operations)
        self._validate_reductions(root["reductions"], root["data_objects"], operations)

        failure = self._mapping(root["failure_semantics"], "failure_semantics")
        self._check_keys(
            failure,
            "failure_semantics",
            required={"status", "success_value", "partial_writes", "commit_partial_results"},
            optional={"diagnostic"},
        )
        self._data_reference(failure["status"], root["data_objects"], "failure_semantics.status")
        if "diagnostic" in failure:
            self._data_reference(
                failure["diagnostic"], root["data_objects"], "failure_semantics.diagnostic"
            )
        if not isinstance(failure["partial_writes"], bool):
            self._error("failure_semantics.partial_writes must be boolean")
        if not isinstance(failure["commit_partial_results"], bool):
            self._error("failure_semantics.commit_partial_results must be boolean")

        grouping = self._mapping(root["baseline_grouping"], "baseline_grouping")
        self._check_keys(
            grouping,
            "baseline_grouping",
            required={"task_function", "kernel_grouping", "allow_fusion", "allow_splitting"},
        )
        for key in ("allow_fusion", "allow_splitting"):
            if not isinstance(grouping[key], bool):
                self._error("baseline_grouping.{} must be boolean".format(key))

    def verify_sources(self, source_root):
        """Verify source hashes, helper signatures, and the entry point.

        Source paths in the contract are resolved relative to *source_root*.
        This keeps application paths out of RecipeTools metadata.
        """
        source_root = Path(source_root).resolve()
        contents = {}
        for role, specification in self.data["sources"].items():
            path = self._resolve_source(source_root, specification["path"])
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise ArithmeticHelperContractError(
                    "Unable to read {} source {!s}: {}".format(role, path, exc)
                ) from exc
            actual = hashlib.sha256(payload).hexdigest()
            if actual != specification["sha256"]:
                self._error(
                    "{} source checksum mismatch for {!s}: expected {}, found {}".format(
                        role, path, specification["sha256"], actual
                    )
                )
            contents[role] = payload.decode("utf-8")

        interfaces = self.parse_helper_interfaces(contents["helpers"])
        expected = self.data["helper_interfaces"]
        for name, arguments in expected.items():
            if name not in interfaces:
                self._error("helper {!r} is not defined in the helper source".format(name))
            if interfaces[name] != arguments:
                self._error(
                    "helper {!r} arguments differ: contract {}, source {}".format(
                        name, arguments, interfaces[name]
                    )
                )
        if self.data.get("require_complete_helper_inventory", False):
            missing = sorted(set(interfaces) - set(expected))
            if missing:
                self._error("helper inventory omits source helpers: {}".format(", ".join(missing)))

        entrypoint = re.compile(
            r"(?im)^\s*subroutine\s+{}\s*\(".format(re.escape(self.data["entrypoint"]))
        )
        if entrypoint.search(contents["arithmetic"]) is None:
            self._error(
                "entrypoint {!r} is not present in the arithmetic source".format(
                    self.data["entrypoint"]
                )
            )

        return {
            role: self._resolve_source(source_root, spec["path"])
            for role, spec in self.data["sources"].items()
        }

    @classmethod
    def parse_helper_interfaces(cls, text):
        """Extract ``name -> formal arguments`` from NewImpl-style helper INI text."""
        lines = text.splitlines()
        interfaces = {}
        for index, raw_line in enumerate(lines):
            if not raw_line or raw_line[0].isspace() or raw_line.lstrip().startswith((";", "#")):
                continue
            name = raw_line.strip()
            if cls._IDENTIFIER.fullmatch(name) is None:
                continue
            next_index = index + 1
            while next_index < len(lines):
                candidate = lines[next_index].strip()
                if candidate and not candidate.startswith((";", "#")):
                    break
                next_index += 1
            if next_index >= len(lines) or not lines[next_index].startswith("args="):
                continue
            arguments_text = lines[next_index].split("=", 1)[1].strip()
            arguments = [] if not arguments_text else [item.strip() for item in arguments_text.split(",")]
            if any(cls._IDENTIFIER.fullmatch(item) is None for item in arguments):
                raise ArithmeticHelperContractError(
                    "Invalid formal argument list for helper {!r}".format(name)
                )
            if name in interfaces:
                raise ArithmeticHelperContractError("Duplicate helper definition {!r}".format(name))
            interfaces[name] = arguments
        return interfaces

    def _validate_sources(self, sources):
        sources = self._mapping(sources, "sources")
        if set(sources) != self._SOURCE_ROLES:
            self._error("sources must contain exactly arithmetic, helpers, and expander")
        for role, source in sources.items():
            source = self._mapping(source, "sources.{}".format(role))
            self._check_keys(source, "sources.{}".format(role), required={"path", "sha256"})
            if not isinstance(source["path"], str) or not source["path"]:
                self._error("sources.{}.path must be a nonempty string".format(role))
            path = Path(source["path"])
            if path.is_absolute() or ".." in path.parts:
                self._error("sources.{}.path must be relative and cannot contain '..'".format(role))
            if not isinstance(source["sha256"], str) or self._SHA256.fullmatch(source["sha256"]) is None:
                self._error("sources.{}.sha256 must be a lowercase SHA-256 digest".format(role))

    def _validate_helper_interfaces(self, interfaces):
        interfaces = self._mapping(interfaces, "helper_interfaces", nonempty=True)
        for name, arguments in interfaces.items():
            self._identifier(name, "helper_interfaces key")
            arguments = self._list(arguments, "helper_interfaces.{}".format(name))
            for index, argument in enumerate(arguments):
                self._identifier(argument, "helper_interfaces.{}[{}]".format(name, index))
            if len(arguments) != len(set(arguments)):
                self._error("helper {!r} has duplicate formal arguments".format(name))

    def _validate_data_objects(self, objects):
        objects = self._mapping(objects, "data_objects", nonempty=True)
        for name, specification in objects.items():
            self._identifier(name, "data_objects key")
            specification = self._mapping(specification, "data_objects.{}".format(name))
            self._check_keys(
                specification,
                "data_objects.{}".format(name),
                required={"kind", "role", "access"},
                optional={"components", "condition", "lifetime", "producer", "consumers", "shape"},
            )
            if specification["kind"] not in {"field", "scratch", "parameter", "scalar", "diagnostic"}:
                self._error("data_objects.{}.kind is unsupported".format(name))
            if not isinstance(specification["role"], str) or not specification["role"]:
                self._error("data_objects.{}.role must be a nonempty string".format(name))
            if "components" in specification:
                components = self._list(
                    specification["components"], "data_objects.{}.components".format(name), nonempty=True
                )
                if len(components) != len(set(components)):
                    self._error("data_objects.{}.components contains duplicates".format(name))
            access = self._list(specification["access"], "data_objects.{}.access".format(name), nonempty=True)
            for index, item in enumerate(access):
                item = self._mapping(item, "data_objects.{}.access[{}]".format(name, index))
                self._check_keys(
                    item,
                    "data_objects.{}.access[{}]".format(name, index),
                    required={"mode", "region"},
                    optional={"condition"},
                )
                if item["mode"] not in self._ACCESS_MODES:
                    self._error("data_objects.{}.access[{}].mode is unsupported".format(name, index))
                if not isinstance(item["region"], str) or not item["region"]:
                    self._error("data_objects.{}.access[{}].region must be nonempty".format(name, index))
            if specification["kind"] == "scratch":
                for key in ("lifetime", "producer", "consumers"):
                    if key not in specification:
                        self._error("scratch data object {!r} requires {!r}".format(name, key))

    def _validate_operations(self, operations):
        operations = self._list(operations, "operations", nonempty=True)
        by_name = {}
        known_data = self.data["data_objects"]
        known_helpers = self.data["helper_interfaces"]
        for index, operation in enumerate(operations):
            label = "operations[{}]".format(index)
            operation = self._mapping(operation, label)
            self._check_keys(
                operation,
                label,
                required={"name", "domain", "helpers", "reads", "writes", "depends_on"},
                optional={"private_scratch", "ordering"},
            )
            name = operation["name"]
            self._identifier(name, "{}.name".format(label))
            if name in by_name:
                self._error("duplicate operation {!r}".format(name))
            by_name[name] = operation
            if not isinstance(operation["domain"], str) or not operation["domain"]:
                self._error("{}.domain must be a nonempty symbolic expression".format(label))
            for key in ("helpers", "reads", "writes", "depends_on"):
                values = self._list(operation[key], "{}.{}".format(label, key))
                if len(values) != len(set(values)):
                    self._error("{}.{} contains duplicates".format(label, key))
            if "private_scratch" in operation:
                private_scratch = self._list(
                    operation["private_scratch"], "{}.private_scratch".format(label)
                )
                for scratch_index, scratch_name in enumerate(private_scratch):
                    self._identifier(
                        scratch_name,
                        "{}.private_scratch[{}]".format(label, scratch_index),
                    )
                if len(private_scratch) != len(set(private_scratch)):
                    self._error("{}.private_scratch contains duplicates".format(label))
            for helper in operation["helpers"]:
                if helper not in known_helpers:
                    self._error("operation {!r} references undeclared helper {!r}".format(name, helper))
            for key in ("reads", "writes"):
                for object_name in operation[key]:
                    self._data_reference(object_name, known_data, "{}.{}".format(label, key))

        for name, operation in by_name.items():
            for dependency in operation["depends_on"]:
                if dependency not in by_name:
                    self._error("operation {!r} depends on unknown operation {!r}".format(name, dependency))
                if dependency == name:
                    self._error("operation {!r} cannot depend on itself".format(name))
        self._check_dependency_cycles(by_name)
        return by_name

    def _validate_scratch_flow(self, objects, operations):
        for name, specification in objects.items():
            if specification["kind"] != "scratch":
                continue
            producer = specification["producer"]
            consumers = self._list(specification["consumers"], "data_objects.{}.consumers".format(name), nonempty=True)
            if producer not in operations:
                self._error("scratch {!r} has unknown producer {!r}".format(name, producer))
            if name not in operations[producer]["writes"]:
                self._error("scratch {!r} producer {!r} does not write it".format(name, producer))
            for consumer in consumers:
                if consumer not in operations:
                    self._error("scratch {!r} has unknown consumer {!r}".format(name, consumer))
                if name not in operations[consumer]["reads"]:
                    self._error("scratch {!r} consumer {!r} does not read it".format(name, consumer))

    def _validate_synchronization(self, synchronization, operations):
        barriers = self._list(synchronization, "synchronization")
        for index, barrier in enumerate(barriers):
            label = "synchronization[{}]".format(index)
            barrier = self._mapping(barrier, label)
            self._check_keys(
                barrier,
                label,
                required={"after", "before", "scope", "reason", "relation"},
            )
            after = barrier["after"]
            before = barrier["before"]
            if after not in operations or before not in operations:
                self._error("{} references an unknown operation".format(label))
            relation = barrier["relation"]
            if relation not in {"direct_dependency", "next_iteration"}:
                self._error("{}.relation is unsupported".format(label))
            if relation == "direct_dependency" and after not in operations[before]["depends_on"]:
                self._error("{} must correspond to a direct operation dependency".format(label))

    def _validate_reductions(self, reductions, objects, operations):
        reductions = self._list(reductions, "reductions")
        for index, reduction in enumerate(reductions):
            label = "reductions[{}]".format(index)
            reduction = self._mapping(reduction, label)
            self._check_keys(reduction, label, required={"target", "operator", "identity", "operation"})
            self._data_reference(reduction["target"], objects, "{}.target".format(label))
            if reduction["operator"] not in self._REDUCTIONS:
                self._error("{}.operator is unsupported".format(label))
            if reduction["operation"] not in operations:
                self._error("{}.operation is unknown".format(label))
            if reduction["target"] not in operations[reduction["operation"]]["writes"]:
                self._error("{} target is not written by its operation".format(label))

    def _check_dependency_cycles(self, operations):
        visiting = set()
        visited = set()

        def visit(name):
            if name in visiting:
                self._error("operation dependencies contain a cycle at {!r}".format(name))
            if name in visited:
                return
            visiting.add(name)
            for dependency in operations[name]["depends_on"]:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in operations:
            visit(name)

    @staticmethod
    def _resolve_source(source_root, relative_path):
        root = source_root.resolve()
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ArithmeticHelperContractError(
                "Source path {!s} escapes source root {!s}".format(path, root)
            ) from exc
        return path

    def _identifier(self, value, label):
        if not isinstance(value, str) or self._IDENTIFIER.fullmatch(value) is None:
            self._error("{} must be an identifier".format(label))

    def _data_reference(self, value, objects, label):
        if value not in objects:
            self._error("{} references undeclared data object {!r}".format(label, value))

    def _mapping(self, value, label, nonempty=False):
        if not isinstance(value, dict) or (nonempty and not value):
            self._error("{} must be {}mapping".format(label, "a nonempty " if nonempty else "a "))
        return value

    def _list(self, value, label, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            self._error("{} must be {}list".format(label, "a nonempty " if nonempty else "a "))
        return value

    def _check_keys(self, mapping, label, required, optional=None):
        optional = set() if optional is None else optional
        missing = required - set(mapping)
        extra = set(mapping) - required - optional
        if missing:
            self._error("{} is missing keys: {}".format(label, ", ".join(sorted(missing))))
        if extra:
            self._error("{} has unknown keys: {}".format(label, ", ".join(sorted(extra))))

    @staticmethod
    def _error(message):
        raise ArithmeticHelperContractError(message)

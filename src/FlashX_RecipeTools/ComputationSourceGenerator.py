"""Deterministic computation-source generation from a validated contract."""

import hashlib
import os
import re
import subprocess
import sys
import tempfile

from pathlib import Path

from .ArithmeticHelperContract import ArithmeticHelperContract


class ComputationSourceGenerationError(RuntimeError):
    """Raised when validated arithmetic cannot be expanded safely."""


class ComputationSourceGenerator:
    """Expand unchanged arithmetic using its verified application expander."""

    _MACRO_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    _UNRESOLVED_MACRO = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*(?:\([^@]*\))?@")
    _UNRESOLVED_PLACEHOLDER = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")

    def __init__(self, contract):
        if not isinstance(contract, ArithmeticHelperContract):
            raise TypeError("contract must be an ArithmeticHelperContract")
        self.contract = contract

    @classmethod
    def _binding_macro_names(cls, binding_text):
        names = []
        for line in binding_text.splitlines():
            if not line or line[0].isspace() or line.lstrip().startswith(("#", ";")):
                continue
            candidate = line.strip()
            if cls._MACRO_NAME.fullmatch(candidate):
                names.append(candidate)
        return names

    def _validate_binding(self, binding_path):
        try:
            binding_text = binding_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ComputationSourceGenerationError(
                "Unable to read layout binding {!s}: {}".format(binding_path, exc)
            ) from exc

        names = self._binding_macro_names(binding_text)
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ComputationSourceGenerationError(
                "Layout binding contains duplicate macros: {}".format(", ".join(duplicates))
            )

        missing = sorted(set(self.contract.data["layout_symbols"]) - set(names))
        if missing:
            raise ComputationSourceGenerationError(
                "Layout binding omits required macros: {}".format(", ".join(missing))
            )

    def _expand(
        self,
        source_paths,
        input_path,
        binding_path,
        output_path,
        unit_kind,
        unit_name,
        overwrite,
    ):
        output_path = Path(output_path).resolve()
        self._validate_binding(binding_path)

        if output_path.exists() and not overwrite:
            raise FileExistsError("Output already exists: {!s}".format(output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temporary = tempfile.NamedTemporaryFile(
            prefix=".{}-".format(output_path.name),
            suffix=".tmp.F90",
            dir=str(output_path.parent),
            delete=False,
        )
        temporary_path = Path(temporary.name)
        temporary.close()

        command = [
            sys.executable,
            str(source_paths["expander"]),
            "--definitions",
            str(binding_path),
            str(source_paths["helpers"]),
            "--input",
            str(input_path),
            "--output",
            str(temporary_path),
            "--reject-duplicates",
        ]

        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "unknown expander failure"
                raise ComputationSourceGenerationError(
                    "Arithmetic expansion failed: {}".format(detail)
                )

            try:
                generated = temporary_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ComputationSourceGenerationError(
                    "Unable to read generated source {!s}: {}".format(temporary_path, exc)
                ) from exc

            unresolved = self._UNRESOLVED_MACRO.search(generated)
            if unresolved is not None:
                raise ComputationSourceGenerationError(
                    "Generated source contains unresolved macro {!r}".format(unresolved.group(0))
                )
            unresolved = self._UNRESOLVED_PLACEHOLDER.search(generated)
            if unresolved is not None:
                raise ComputationSourceGenerationError(
                    "Generated source contains unresolved placeholder {!r}".format(
                        unresolved.group(0)
                    )
                )

            program_unit = re.compile(
                r"(?im)^\s*{}\s+{}(?:\s*\(|\s*$)".format(
                    re.escape(unit_kind), re.escape(unit_name)
                )
            )
            if program_unit.search(generated) is None:
                raise ComputationSourceGenerationError(
                    "Generated source omits {} {!r}".format(
                        unit_kind, unit_name
                    )
                )

            os.replace(str(temporary_path), str(output_path))
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return output_path

    def generate(self, source_root, layout_binding, output, overwrite=False):
        """Validate all inputs and atomically generate the contracted source."""
        source_paths = self.contract.verify_sources(source_root)
        return self._expand(
            source_paths,
            source_paths["arithmetic"],
            Path(layout_binding).resolve(),
            Path(output).resolve(),
            "subroutine",
            self.contract.data["entrypoint"],
            overwrite,
        )

    def generate_auxiliary(
        self,
        source_root,
        source_name,
        source_sha256,
        layout_binding,
        output,
        unit_kind,
        unit_name,
        overwrite=False,
    ):
        """Generate a checksummed companion source with the contracted tools."""
        source_paths = self.contract.verify_sources(source_root)
        relative_source = Path(source_name)
        if relative_source.is_absolute() or ".." in relative_source.parts:
            raise ComputationSourceGenerationError(
                "Auxiliary source path must be relative and cannot contain '..'"
            )
        if unit_kind.lower() not in {"program", "subroutine", "function"}:
            raise ComputationSourceGenerationError(
                "Unsupported Fortran program unit kind {!r}".format(unit_kind)
            )

        input_path = Path(source_root).resolve().joinpath(relative_source)
        try:
            payload = input_path.read_bytes()
        except OSError as exc:
            raise ComputationSourceGenerationError(
                "Unable to read auxiliary source {!s}: {}".format(input_path, exc)
            ) from exc
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != source_sha256:
            raise ComputationSourceGenerationError(
                "Auxiliary source checksum mismatch for {!s}: expected {}, found {}".format(
                    input_path, source_sha256, actual_sha256
                )
            )

        return self._expand(
            source_paths,
            input_path,
            Path(layout_binding).resolve(),
            Path(output).resolve(),
            unit_kind.lower(),
            unit_name,
            overwrite,
        )

"""Application-owned lowering for legal NewImpl face-flux groupings.

This module does not infer dependencies or parse arbitrary Fortran.  It uses
checked anchors in the checksum-verified NewImpl entry point and lowers only
the groupings approved by ``newimpl_face_flux.boundaries.json``.
"""

from FlashX_RecipeTools import ComputationSourceGenerationError


FULLY_FUSED = "fully_fused"
FLATTENING_THEN_DIRECTIONAL = "flattening_then_directional"
FLATTENING_RECONSTRUCTION_SOLVE = "flattening_reconstruction_solve"


_PUBLIC = "  public :: cell_field, flux_field, hy_getFaceFlux\n"
_ADAPTER_USE = (
    "  use newimpl_hydro, only: cell_field, flux_field, hydro_parameters, "
    "hydro_workspace, &\n"
    "                           hy_getFaceFlux, HY_BAD_INPUT\n"
)
_ARGUMENTS = (
    "data,flux,block,lo,hi,availableLo,availableHi,ndim, &\n"
    "                           inputMap,outputMap,shockVariable,params,work,"
    "maxSpeed,status,failedFace"
)
_CALL_ARGUMENTS = (
    "data, flux, block, lo, hi, availableLo, availableHi, ndim, &\n"
    "      inputMap, outputMap, shockVariable, params, work, maxSpeed, status, "
    "failedFace"
)


def adapter_names(grouping):
    """Return the ordered TaskFunction entry points for a legal grouping."""
    if grouping == FULLY_FUSED:
        return ("newimpl_face_flux_adapter",)
    if grouping == FLATTENING_THEN_DIRECTIONAL:
        return (
            "newimpl_face_flux_flattening_adapter",
            "newimpl_face_flux_directional_x_adapter",
            "newimpl_face_flux_directional_y_adapter",
        )
    if grouping == FLATTENING_RECONSTRUCTION_SOLVE:
        return (
            "newimpl_face_flux_flattening_adapter",
            "newimpl_face_flux_reconstruct_x_adapter",
            "newimpl_face_flux_solve_x_adapter",
            "newimpl_face_flux_reconstruct_y_adapter",
            "newimpl_face_flux_solve_y_adapter",
        )
    raise ComputationSourceGenerationError(
        "Unsupported NewImpl grouping {!r}".format(grouping)
    )


def _one_index(lines, text):
    matches = [index for index, line in enumerate(lines) if line.strip() == text]
    if len(matches) != 1:
        raise ComputationSourceGenerationError(
            "Expected exactly one NewImpl grouping anchor {!r}, found {}".format(
                text, len(matches)
            )
        )
    return matches[0]


def _routine_header(name, directional=False):
    suffix = ",direction" if directional else ""
    return (
        "  subroutine {}({}{})\n".format(name, _ARGUMENTS, suffix)
    )


def _phase_declarations(declarations, directional):
    if not directional:
        return declarations
    declarations = declarations.replace(
        "real(rk), intent(out) :: maxSpeed",
        "real(rk), intent(inout) :: maxSpeed",
    ).replace(
        "integer, intent(out) :: status,failedFace(4)",
        "integer, intent(inout) :: status,failedFace(4)",
    )
    return declarations + "    integer, intent(in) :: direction\n"


def _call(name, directional=False, indent="    "):
    suffix = ", d" if directional else ""
    return (
        "{}call {}( &\n{}  {}{})\n".format(
            indent, name, indent, _CALL_ARGUMENTS, suffix
        )
    )


def _phase_routine(name, declarations, body, directional=False):
    result = [_routine_header(name, directional)]
    result.append(_phase_declarations(declarations, directional))
    if directional:
        result.extend(
            [
                "    if (status/=HY_OK .or. direction<1 .or. "
                "direction>ndim) return\n",
                "    d=direction\n",
            ]
        )
    result.append(body)
    if directional and name in {
        "hy_faceFluxDirectional",
        "hy_faceFluxSolveDirection",
    }:
        result.append(
            "    if (status==HY_OK .and. direction==ndim) failedFace=0\n"
        )
    result.append("  end subroutine {}\n\n".format(name))
    return "".join(result)


def _dispatcher(declarations, grouping):
    result = [_routine_header("hy_getFaceFlux")]
    result.append(declarations)
    result.append(_call("hy_faceFluxFlattening"))
    result.append("    if (status/=HY_OK) return\n")
    result.append("    do d=1,ndim\n")
    if grouping == FLATTENING_THEN_DIRECTIONAL:
        result.append(_call("hy_faceFluxDirectional", True, "      "))
    else:
        result.append(_call("hy_faceFluxReconstructDirection", True, "      "))
        result.append(_call("hy_faceFluxSolveDirection", True, "      "))
    result.append("      if (status/=HY_OK) return\n")
    result.append("    end do\n")
    result.append("    status=HY_OK; failedFace=0\n")
    result.append("  end subroutine hy_getFaceFlux\n\n")
    return "".join(result)


def grouped_arithmetic_transform(grouping):
    """Return a deterministic source transform for one validated grouping."""
    if grouping == FULLY_FUSED:
        return lambda source: source
    if grouping not in {
        FLATTENING_THEN_DIRECTIONAL,
        FLATTENING_RECONSTRUCTION_SOLVE,
    }:
        raise ComputationSourceGenerationError(
            "Unsupported NewImpl grouping {!r}".format(grouping)
        )

    def transform(source):
        lines = source.splitlines(keepends=True)
        contains = _one_index(lines, "contains")
        macro_imports = _one_index(lines, "!$macro_imports")
        macro_declarations = _one_index(lines, "!$macro_declarations")
        preflight_start = _one_index(
            lines, "status=HY_BAD_INPUT; failedFace=0; maxSpeed=0"
        )
        preflight_end = _one_index(
            lines, "if (any(work%lo>flo) .or. any(work%hi<fhi)) return"
        )
        flatten = _one_index(
            lines,
            "@hy_computeFlattening(data,inputMap,block,flo,fhi,ndim,params,"
            "work%flat,status)@",
        )
        direction_loop = _one_index(lines, "do d=1,ndim")
        direction_setup = _one_index(lines, "e=0; e(d)=1; rlo=lo-e; rhi=hi+e")
        reconstruction = _one_index(
            lines,
            "@hy_reconstructDirection(data,inputMap,block,rlo,rhi,e,work%flat,"
            "params,work%minus,work%plus)@",
        )
        face_setup = _one_index(lines, "fhi=hi+e")
        final_status = _one_index(lines, "status=HY_OK; failedFace=0")

        if not (
            contains < macro_imports < macro_declarations < preflight_start
            <= preflight_end < flatten < direction_loop < direction_setup
            < reconstruction < face_setup < final_status
        ):
            raise ComputationSourceGenerationError(
                "NewImpl grouping anchors are not in the contracted order"
            )
        if lines[final_status - 1].strip() != "end do":
            raise ComputationSourceGenerationError(
                "NewImpl direction-loop closing anchor changed"
            )

        prefix = "".join(lines[: contains + 1])
        declarations = "".join(lines[macro_imports : macro_declarations + 1])
        preflight = "".join(lines[preflight_start : preflight_end + 1])
        flatten_body = preflight + lines[flatten]
        direction_body = "".join(lines[direction_setup : final_status - 1])
        reconstruct_body = "".join(
            lines[direction_setup : reconstruction + 1]
        )
        solve_body = lines[direction_setup] + "".join(
            lines[face_setup : final_status - 1]
        )

        if grouping == FLATTENING_THEN_DIRECTIONAL:
            phase_names = ["hy_faceFluxFlattening", "hy_faceFluxDirectional"]
        else:
            phase_names = [
                "hy_faceFluxFlattening",
                "hy_faceFluxReconstructDirection",
                "hy_faceFluxSolveDirection",
            ]
        public = "  public :: cell_field, flux_field, hy_getFaceFlux, &\n"
        public += "             {}\n".format(", ".join(phase_names))
        if _PUBLIC not in prefix:
            raise ComputationSourceGenerationError(
                "NewImpl public-entrypoint anchor changed"
            )
        prefix = prefix.replace(_PUBLIC, public)

        result = [prefix]
        result.append(
            _phase_routine(
                "hy_faceFluxFlattening", declarations, flatten_body
            )
        )
        if grouping == FLATTENING_THEN_DIRECTIONAL:
            result.append(
                _phase_routine(
                    "hy_faceFluxDirectional",
                    declarations,
                    direction_body,
                    directional=True,
                )
            )
        else:
            result.append(
                _phase_routine(
                    "hy_faceFluxReconstructDirection",
                    declarations,
                    reconstruct_body,
                    directional=True,
                )
            )
            result.append(
                _phase_routine(
                    "hy_faceFluxSolveDirection",
                    declarations,
                    solve_body,
                    directional=True,
                )
            )
        result.append(_dispatcher(declarations, grouping))
        result.append("end module\n")
        return "".join(result)

    return transform


def grouped_adapter_source(source, grouping):
    """Lower the existing layout adapter to calls at legal phase boundaries."""
    if grouping == FULLY_FUSED:
        return source
    if _ADAPTER_USE not in source:
        raise ComputationSourceGenerationError(
            "NewImpl adapter import anchor changed"
        )

    if grouping == FLATTENING_THEN_DIRECTIONAL:
        phase_names = "hy_faceFluxFlattening, hy_faceFluxDirectional"
    elif grouping == FLATTENING_RECONSTRUCTION_SOLVE:
        phase_names = (
            "hy_faceFluxFlattening, hy_faceFluxReconstructDirection, &\n"
            "                           hy_faceFluxSolveDirection"
        )
    else:
        raise ComputationSourceGenerationError(
            "Unsupported NewImpl grouping {!r}".format(grouping)
        )
    replacement_use = (
        "  use newimpl_hydro, only: cell_field, flux_field, hydro_parameters, "
        "hydro_workspace, &\n"
        "                           hy_getFaceFlux, {}, HY_BAD_INPUT\n".format(
            phase_names
        )
    )
    result = source.replace(_ADAPTER_USE, replacement_use)

    call_start = result.find("    call hy_getFaceFlux( &")
    if call_start < 0:
        raise ComputationSourceGenerationError(
            "NewImpl adapter call anchor changed"
        )
    call_end_text = "      status(1), failed_face(1:4))\n"
    call_end = result.find(call_end_text, call_start)
    if call_end < 0:
        raise ComputationSourceGenerationError(
            "NewImpl adapter call-end anchor changed"
        )
    call_end += len(call_end_text)

    actuals = (
        "state_view, flux_view, 1, tile_lo, tile_hi, tile_lbound, available_hi, &\n"
        "        ndim, input_map, output_map, 8, parameters, workspace, "
        "max_speed(1), &\n"
        "        status(1), failed_face(1:4)"
    )
    module_end = result.rfind("end module")
    contains = result.find("contains\n")
    subroutine_start = result.find("  subroutine newimpl_face_flux_adapter(")
    if contains < 0 or subroutine_start < 0 or module_end < 0:
        raise ComputationSourceGenerationError(
            "NewImpl adapter module anchors changed"
        )
    module_header = result[: contains + len("contains\n")]
    subroutine = result[subroutine_start:module_end]

    phases = []
    if grouping == FLATTENING_THEN_DIRECTIONAL:
        phases = [
            (adapter_names(grouping)[0], "hy_faceFluxFlattening", None),
            (adapter_names(grouping)[1], "hy_faceFluxDirectional", 1),
            (adapter_names(grouping)[2], "hy_faceFluxDirectional", 2),
        ]
    else:
        phases = [
            (adapter_names(grouping)[0], "hy_faceFluxFlattening", None),
            (adapter_names(grouping)[1], "hy_faceFluxReconstructDirection", 1),
            (adapter_names(grouping)[2], "hy_faceFluxSolveDirection", 1),
            (adapter_names(grouping)[3], "hy_faceFluxReconstructDirection", 2),
            (adapter_names(grouping)[4], "hy_faceFluxSolveDirection", 2),
        ]

    public_anchor = "  public :: newimpl_face_flux_adapter\n"
    if public_anchor not in module_header:
        raise ComputationSourceGenerationError(
            "NewImpl adapter public anchor changed"
        )
    module_header = module_header.replace(
        public_anchor,
        "  public :: newimpl_face_flux_adapter, &\n            {}\n".format(
            ", &\n            ".join(adapter_names(grouping))
        ),
    )
    routines = [subroutine]
    for adapter, phase, direction in phases:
        if direction is None:
            call = "    call {}( &\n      {} )\n".format(phase, actuals)
        else:
            call = "    call {}( &\n      {}, {})\n".format(
                phase, actuals, direction
            )
        routine = subroutine[:call_start - subroutine_start] + call + subroutine[
            call_end - subroutine_start:
        ]
        routine = routine.replace("newimpl_face_flux_adapter", adapter)
        routines.append(routine)
    return module_header + "".join(routines) + "end module newimpl_face_flux_adapter_mod\n"

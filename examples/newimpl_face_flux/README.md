# NewImpl face-flux arithmetic contract

This example records the application-supplied contract for the layout-neutral
NewImpl face-flux stage and generates its Milhoja HOSTMEM computation,
TaskFunction, and DataPacket sources. It does not change the maintained
arithmetic.

From an environment containing FlashX-RecipeTools, validate it with:

```sh
python validate_contract.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl
```

The validator checks the three source hashes, the `hy_getFaceFlux` entry point,
the complete helper inventory, and all contract-level data, dependency, scratch,
synchronization, reduction, and failure declarations.

Generate the computation source with:

```sh
python generate_computation.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  generated/newimpl_face_flux_milhoja.F90
```

The default is `--layout variable-last`. Pass `--layout variable-first` and a
different output path to generate the alternative component ordering.

Generation validates the contract and all source hashes before invoking the
contracted `macro_expand.py`.  `milhoja_host_layout.ini` binds the logical field
references to pointer-backed arrays using Milhoja's current spatial-first view,
with variable and batched tile/block indices following.  The generated source contains the unchanged
`hy_getFaceFlux` ordering and error behavior.  Generation fails if a required
layout symbol is absent, a macro remains unresolved, or the output already
exists; pass `--overwrite` only when replacement is intended.

The generated field pointers are views. The TaskFunction adapter described
below associates them with DataPacket storage and manages the reusable
workspace.

The `generated/newimpl_face_flux_milhoja.F90` file in this example was produced
from the checksummed NewImpl sources using that command.

## Standalone test

Generate the checksummed NewImpl test driver with the same helpers and layout:

```sh
python generate_test.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  generated/test_newimpl_face_flux_milhoja.F90
```

The test-source checksum is recorded in `generate_test.py`. The generator also
revalidates the Step 2 contract and its arithmetic, helper, and expander hashes
before expanding the test.

On the target platform, compile and run both generated sources together. For
example, with GNU Fortran:

```sh
mkdir -p build/test
gfortran -std=f2003 -Wall -Wextra -fcheck=all \
  -J build/test -I build/test \
  generated/newimpl_face_flux_milhoja.F90 \
  generated/test_newimpl_face_flux_milhoja.F90 \
  -o build/test/test_newimpl_face_flux_milhoja

build/test/test_newimpl_face_flux_milhoja
```

A successful run prints `hydro tests passed`. These checks cover dimensional
reductions, constant-state physical fluxes, WENO reconstruction, flattening,
state floors, stationary-contact and Sod fluxes, hybrid HLLE behavior,
viscosity, vacuum handling, permuted variable maps, two block IDs, and explicit
failure returns. This is a standalone computation/layout test; it does not yet
exercise Milhoja scheduling or DataPacket transfers.

## HOSTMEM TaskFunction and DataPacket

Generate the complete Step 3D source set with a Milhoja installation configured
for the two-dimensional HOSTMEM runtime with DataPacket support:

```sh
python generate_taskfunction.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  /path/to/Milhoja/2D-hostmem \
  generated/taskfunction
```

Generate both supported layouts into separate directories with:

```sh
python generate_taskfunction.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  /path/to/Milhoja/2D-hostmem \
  generated/taskfunction \
  --layout variable-last

python generate_taskfunction.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  /path/to/Milhoja/2D-hostmem \
  generated/taskfunction_variable_first \
  --layout variable-first
```

The default tile interior is 16 by 16 cells. Use `--nxb` and `--nyb` when the
target Flash-X setup uses different values. Existing output is protected unless
`--overwrite` is supplied.

Generation first revalidates the Step 2 contract and NewImpl source hashes. It
then produces:

- `newimpl_face_flux.taskfunction.json`, the assembled TaskFunction specification
- `newimpl_face_flux.mapping.json`, the contract-to-TaskFunction binding
- `DataPacket_newimpl_face_flux_tf.{h,cxx}` and its Fortran construction module
- `newimpl_face_flux_tf.cxx`, the C++ runtime wrapper
- `newimpl_face_flux_tf_C2F.F90`, the C-to-Fortran interface
- `newimpl_face_flux_tf_mod.F90`, the host-executed Fortran TaskFunction
- `newimpl_face_flux_adapter_mod.F90`, the per-tile view adapter
- `newimpl_face_flux_milhoja.F90`, the unchanged generated computation

There is one TaskFunction call containing the whole face-flux stage. The state
is packed as input, the X and Y flux arrays are unpacked as outputs, and the
directional flux views point directly at those packet arrays. Flattening and
reconstruction workspaces, `max_speed`, `status`, and `failed_face` have
per-tile scratch allocation metadata. The latter three results currently remain
packet-internal scratch; exposing them to a caller is an integration concern for
the runtime test, not an arithmetic change.

This step validates source generation only. Compiling and running these files
requires a Milhoja runtime test/application target that supplies tiles and the
ten external parameter values; that target belongs to the next integration
step.

## Step 3E verification

Run the host-side generation verification with:

```sh
python verify_taskfunction.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  /path/to/Milhoja/2D-hostmem
```

This rechecks the source hashes and contract-to-spec translation, validates the
generated argument and scratch descriptions, checks the complete output file
set, rejects OpenACC/CUDA content, and generates twice with different Python
hash seeds to prove byte-for-byte determinism.

The runtime comparison in `runtime_test` executes the generated TaskFunction
using a real generated DataPacket and Milhoja's HOSTMEM `RuntimeBackend`. It
compares that result against a direct call through the NewImpl adapter. Packet
diagnostic scratch is captured after the TaskFunction and before unpacking.

Build and run it on the target platform with:

```sh
cd runtime_test
make MILHOJA_PREFIX=/path/to/Milhoja/2D-hostmem
make run MILHOJA_PREFIX=/path/to/Milhoja/2D-hostmem
```

On macOS, the default final link uses `-lc++`. On a GNU/Linux system, pass
`CXX_RUNTIME=-lstdc++` to both `make` commands if needed.
The final link uses `mpifort` because Milhoja's logger references MPI even
though this comparison itself runs as a single process. Override `LINKER` if
your MPI Fortran wrapper has a different name.

The driver runs a one-direction case, a two-direction case, and an intentional
solver failure. It compares X/Y face fluxes as applicable, `max_speed`, status,
and all four failed-face diagnostic integers. Success ends with:

```text
NewImpl HOSTMEM runtime comparisons passed
```

## Step 4A layout audit

`LAYOUT_CONTRACT.md` records the existing variable-last layout and the proposed
variable-first layout, including exact packet shapes, logical bounds, linear
offsets, and the required state/flux packing permutation. It also identifies
every generator layer that must consume one layout selection in Step 4B.

Step 4B adds both generation-time choices. Variable-last remains the default
for compatibility. Variable-first generation records its selection in the
TaskFunction and mapping JSON, emits component-first C-to-Fortran and scratch
shapes, and generates DataPacket permutations between the existing
variable-last tile storage and the variable-first packet. The arithmetic
sources and hashes are unchanged.

`verify_taskfunction.py` now generates both layouts twice, checks their shapes,
packing strategy, metadata, file sets, host-only content, and byte-for-byte
determinism. Runtime equivalence of both generated layouts is Step 4D.

## Step 4C host-side layout-transform verification

Step 4C numerically verifies the layout mappings independently of the Milhoja
runtime and the face-flux arithmetic. It exercises two batched tiles, full and
partial state-component packing, X- and Y-face flux unpacking, and flattening
and reconstruction scratch offsets. Both variable-last and variable-first
offset maps must be bijective and preserve the same logical values.

Run the focused check with:

```sh
python verify_layout_transforms.py
```

The full generation verifier also runs this check before inspecting generated
sources:

```sh
python verify_taskfunction.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl \
  /path/to/Milhoja/2D-hostmem
```

This stage does not execute a TaskFunction. Runtime equivalence through
Milhoja HOSTMEM remains Step 4D.

## Step 4D dual-layout HOSTMEM runtime comparison

The runtime driver keeps its `TileFlashxr` buffers in the existing
variable-last order. For the direct arithmetic reference it allocates arrays
in the selected generated layout. In the variable-first build, flux comparison
therefore transposes the direct result logically before comparing it with the
unpacked Tile buffer.

Build and run each layout in an isolated directory:

```sh
cd runtime_test

make run LAYOUT=variable-last \
  MILHOJA_PREFIX=/path/to/Milhoja/2D-hostmem

make run LAYOUT=variable-first \
  MILHOJA_PREFIX=/path/to/Milhoja/2D-hostmem
```

Each run exercises constant 1D and 2D inputs and an intentional solver
failure. It compares face fluxes, `max_speed`, status, and all failed-face
diagnostics against a direct call through the matching layout adapter. The
layout-specific build directories prevent Fortran modules or objects from one
layout being reused by the other.

## Step 7 legal computational boundaries

`newimpl_face_flux.boundaries.json` declares the finite set of legal kernel
cuts and grouping candidates for the unchanged face-flux arithmetic.
`BOUNDARY_CONTRACT.md` documents the associated live intermediates, iteration
domains, scratch lifetimes, synchronization, numerical ordering, failure
behavior, and prohibited transformations.

Validate the declaration and its binding to the checksummed NewImpl sources:

```sh
python verify_boundaries.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl
```

The approved candidates are `fully_fused`,
`flattening_then_directional`, and `flattening_reconstruction_solve`. They all
retain one TaskFunction and one resident DataPacket. This step does not select
a grouping or generate split kernels; those changes belong to Step 8.

# NewImpl face-flux layout contract

This document is the Step 4A audit and design contract. Step 4B implements its
two generation-time choices. Each generated source set uses one layout, while
both layouts remain supported from the same unchanged arithmetic.

## Terminology and invariants

`variable-last` and `variable-first` describe the position of the component
axis relative to the spatial axes. The batched tile axis remains last in both
layouts so that each tile occupies one contiguous packet region.

- Variable-last: `(i, j, k, variable, tile)`
- Variable-first: `(variable, i, j, k, tile)`

Flux direction is not an array axis. Milhoja supplies separate X- and Y-flux
pointers, and the arithmetic collects those pointers in `flux%directions`.

The layout choice must not change:

- the checksummed NewImpl arithmetic or helper definitions;
- logical component maps (`input_map=1:7`, `output_map=1:5`);
- cell, face, and workspace index bounds;
- operation order, branches, failure behavior, or the `max_speed` reduction;
- the number or type of stored values; or
- the fact that scratch and packet data are contiguous per tile.

For the current two-dimensional configuration, define:

```text
nxg = nxb + 2*nguard
nyg = nyb + 2*nguard
nzg = 1
nxw = nxb + 2
nyw = nyb + 2
nstate = 8
nflux = 5
nreconstructed = 7
```

The runtime test uses `nxb=16`, `nyb=16`, and `nguard=3`, but the contract is
parameterized by these values.

## Existing variable-last layout

This is the only layout implemented at the end of Step 3.

| Object | Batched packet shape | Per-tile logical bounds |
| --- | --- | --- |
| Cell state | `(nxg, nyg, nzg, 8, ntiles)` | `(tile_lbound(1):available_hi(1), tile_lbound(2):available_hi(2), tile_lbound(3):available_hi(3), 1:8)` |
| X face flux | `(nxb+1, nyb, 1, 5, ntiles)` | `(tile_lo(1):tile_hi(1)+1, tile_lo(2):tile_hi(2), tile_lo(3):tile_hi(3), 1:5)` |
| Y face flux | `(nxb, nyb+1, 1, 5, ntiles)` | `(tile_lo(1):tile_hi(1), tile_lo(2):tile_hi(2)+1, tile_lo(3):tile_hi(3), 1:5)` |
| Flattening scratch | `(nxw, nyw, 1, 1, ntiles)` | `(tile_lo(1)-1:tile_hi(1)+1, tile_lo(2)-1:tile_hi(2)+1, tile_lo(3):tile_hi(3), 1:1)` |
| Minus reconstruction | `(nxw, nyw, 1, 7, ntiles)` | same spatial bounds, component `1:7` |
| Plus reconstruction | `(nxw, nyw, 1, 7, ntiles)` | same spatial bounds, component `1:7` |

For zero-based local indices, an element in a per-tile variable-last region has
the linear offset

```text
i + nx * (j + ny * (k + nz * variable))
```

where `i` is the unit-stride index. The current C-to-Fortran interface creates
these five-dimensional shapes, the TaskFunction wrapper slices the final tile
axis, and the adapter associates the resulting four-dimensional arrays with
the five-dimensional arithmetic views using a one-element block axis.

The current `TileFlashxr` state and flux pointers have this same
spatial-first/component-last order. Consequently, the generated DataPacket can
pack and unpack selected component ranges with contiguous `memcpy` operations.

## Required variable-first layout

The alternative layout places the component axis at unit stride while retaining
the tile axis last.

| Object | Batched packet shape | Per-tile logical bounds |
| --- | --- | --- |
| Cell state | `(8, nxg, nyg, nzg, ntiles)` | `(1:8, tile_lbound(1):available_hi(1), tile_lbound(2):available_hi(2), tile_lbound(3):available_hi(3))` |
| X face flux | `(5, nxb+1, nyb, 1, ntiles)` | `(1:5, tile_lo(1):tile_hi(1)+1, tile_lo(2):tile_hi(2), tile_lo(3):tile_hi(3))` |
| Y face flux | `(5, nxb, nyb+1, 1, ntiles)` | `(1:5, tile_lo(1):tile_hi(1), tile_lo(2):tile_hi(2)+1, tile_lo(3):tile_hi(3))` |
| Flattening scratch | `(1, nxw, nyw, 1, ntiles)` | `(1:1, tile_lo(1)-1:tile_hi(1)+1, tile_lo(2)-1:tile_hi(2)+1, tile_lo(3):tile_hi(3))` |
| Minus reconstruction | `(7, nxw, nyw, 1, ntiles)` | component `1:7` followed by the same spatial bounds |
| Plus reconstruction | `(7, nxw, nyw, 1, ntiles)` | component `1:7` followed by the same spatial bounds |

For zero-based local indices, an element in a per-tile variable-first region has
the linear offset

```text
variable + nvar * (i + nx * (j + ny * k))
```

The arithmetic bindings for this layout are logically:

```text
cell_ref(data,var,block,i,j,k) = data%values(var,i,j,k,block)
face_ref(data,var,block,dir,i,j,k) =
    data%directions(dir)%values(var,i,j,k,block)
```

The arithmetic call sites therefore remain unchanged.

## Source-to-packet packing

For the current `TileFlashxr` API, `dataPtr()` and `fluxDataPtrs()` expose raw
pointers but no layout or stride descriptor. The current source storage must
therefore be treated as variable-last.

- A variable-last packet can continue to use contiguous copies.
- A variable-first packet must transpose state values from
  `(i,j,k,variable)` to `(variable,i,j,k)` while packing.
- Variable-first X and Y fluxes must be transposed back from
  `(variable,i,j,k)` to `(i,j,k,variable)` while unpacking.
- Scratch has no tile source or destination and needs no pack/unpack
  transformation, but its generated shape must follow the selected layout.

The element counts and byte counts are identical for both layouts. Only their
strides differ. A future Tile layout descriptor could remove the assumption
about source storage, but it is not part of Step 4.

## Required consumers of the layout selection

One generation-time selection must control all of the following:

1. The macro binding used to generate the computation (`cell_ref`, `face_ref`,
   `flat_ref`, and allocation helpers).
2. TaskFunction and scratch extents in the group and assembled specifications.
3. DataPacket state/flux shapes, offsets, packing loops, and unpacking loops.
4. C-to-Fortran pointer shapes and TaskFunction per-tile slicing.
5. Adapter dummy-array interpretation and pointer association.
6. Runtime-test allocation, initialization, and result comparison.

Changing only the macro binding would reinterpret variable-last bytes as
variable-first and is invalid.

Tile metadata remains layout-independent with shape `(MILHOJA_MDIM, ntiles)`.
External scalars, `max_speed`, `status`, and `failed_face` are also unchanged.

## Audit findings

- `milhoja_host_layout.ini` currently fixes arithmetic views to
  `(i,j,k,variable,block)`.
- `generate_taskfunction.py` currently emits scratch extents in spatial-first
  order and has no layout field or command-line selection.
- `newimpl_face_flux_adapter_mod.F90` independently assumes spatial-first
  TaskFunction arguments.
- Milhoja's generated C-to-Fortran shapes are spatial-first for grid data.
- Milhoja's generated DataPacket relies on contiguous copies from and to the
  existing variable-last tile pointers.
- The contract-to-TaskFunction mapping records logical variables but not their
  physical ordering.

Therefore Step 4B requires a coordinated generic generator extension; a second
layout INI file alone is insufficient.

## Step 4B implementation boundary

Step 4B introduces one explicit selector with the canonical values
`variable-last` and `variable-first`. Generation must reject an unknown value.
The selected value must be recorded in generated specifications and mapping
metadata, and all six consumers above must derive their shapes or access rules
from it. Neither generated layout may require hand editing.


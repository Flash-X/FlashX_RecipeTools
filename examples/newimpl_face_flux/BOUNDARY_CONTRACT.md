# NewImpl face-flux legal kernel boundaries

This document records the human-readable rationale for
`newimpl_face_flux.boundaries.json`. The JSON declaration is authoritative and
is validated against the checksummed Step 2 arithmetic contract. It declares a
finite set of application-approved cuts; it does not infer dependencies from
Fortran and is not a compiler intermediate representation.

## Reference schedule

The complete `hy_getFaceFlux` stage retains this sequence:

1. Initialize `status`, `failed_face`, and `max_speed`, then validate the
   invocation, mappings, parameters, available guard cells, and workspace.
2. Compute flattening over `lo-active_unit:hi+active_unit`.
3. For each direction `d=1:ndim`, in ascending order:
   1. reconstruct over `lo-unit(d):hi+unit(d)`;
   2. solve faces over `lo:hi+unit(d)`;
   3. stop immediately on a non-`HY_OK` status.

No legal grouping changes this schedule, helper order, branch structure, face
traversal, or error behavior.

## Operation dataflow

| Operation | Domain | Live inputs | Produced values | Private lifetime |
|---|---|---|---|---|
| `compute_flattening` | `lo-active_unit:hi+active_unit` | state, input map, parameters | flattening workspace, status | flattening cell temporaries |
| `reconstruct_direction` | one direction over `lo-unit(d):hi+unit(d)` | state, input map, parameters, flattening | minus and plus reconstructed states | stencil, WENO candidates, and WENO weights for one cell/component |
| `solve_faces` | the same direction over `lo:hi+unit(d)` | state, maps, parameters, reconstructed states | directional face flux, status, failed face, `max_speed` | primitive/conservative states, physical fluxes, star states, and selected face flux for one face |

The flattening workspace lives for the complete face-flux stage. The minus and
plus reconstruction arrays live for one direction and are overwritten by the
next direction. Face-solver temporaries are private to one face and cannot be
promoted to a legal kernel boundary.

## Legal boundaries

| Boundary | Values that must remain live | Required ordering |
|---|---|---|
| `after_flattening` | flattening and status | flattening completes and status is checked before reconstruction |
| `after_reconstruction` | minus and plus reconstructed states for the current direction | reconstruction completes before the face solver consumes either array |
| `direction_transition` | face flux, accumulated `max_speed`, status, and failure diagnostic | face solving and its failure check complete before reconstruction overwrites directional scratch |

When both sides of a boundary remain in one kernel, ordinary program order is
sufficient. When Step 8 selects a cut, the values listed by the boundary must
remain device-resident and the producer kernel must complete before its
consumer starts.

## Legal grouping candidates

The declaration approves exactly three candidates for Step 8 selection:

1. `fully_fused`: flattening, the reference direction loop, reconstruction,
   and face solving remain in one kernel.
2. `flattening_then_directional`: one flattening kernel followed by a kernel
   containing the ordered per-direction reconstruction/solve sequence.
3. `flattening_reconstruction_solve`: one flattening kernel, followed for each
   direction by a reconstruction kernel and then a face-solve kernel.

All candidates remain inside one Milhoja TaskFunction and one resident
DataPacket. Step 7 declares and validates them; Step 8's
`generate_taskfunction.py --grouping` option lowers the selected implementation.

## Numerical and failure constraints

- `max_speed` keeps identity zero, the `max` operator, the same candidate set,
  direction order, face order, and NaN behavior. A reassociated parallel
  reduction is not legal.
- The first failure stops later face and direction arithmetic. A later entry
  in a statically generated call graph may be launched, but it must inspect
  status and return before numerical work. The same `failed_face` is retained,
  and partial results are not committed when the arithmetic contract says not
  to commit them.
- All directions cannot be reconstructed before solving because the minus and
  plus arrays are directionally reused.
- Directions cannot execute concurrently with the current scratch contract.
- The face-solver helper chain cannot be split: its intermediate states and
  branch decisions are face-private and its ordering is fixed.
- Kernel decomposition does not create additional TaskFunctions.

## Verification

Run:

```sh
python verify_boundaries.py \
  /path/to/Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl
```

This verifies the boundary declaration, its binding to the exact arithmetic
contract file, all three NewImpl source hashes, helper interfaces, operation
order, synchronization edges, live-value flow, materialization, grouping
partitions, and preservation constraints.

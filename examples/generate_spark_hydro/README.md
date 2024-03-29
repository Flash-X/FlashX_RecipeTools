# Example: Spark Hydro

## Files
- file `_spark_nodes.py` has definitions of graph nodes in form of classes (inherited from cg-kit)
- file `genSparkHydro.py` has recipe codes and the `main` function

## Recipes

Recipes exist for the variants:
- `amrex_tele` uses AMReX and telescoping
- `pm_tele` uses Paramesh and telescoping
- `pm_nontele` uses Paramesh and *no* telescoping

Run as
```bash
python genSparkHydro.py VARIANT_NAME
```
with `VARIANT_NAME` being one of `amrex_tele`, `pm_tele`, `pm_nontele`.

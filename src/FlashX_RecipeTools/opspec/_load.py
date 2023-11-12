import json
from pathlib import Path
from ._preprocessor import preprocess


def load(fname, pp, **kwargs):
    kwargs.setdefault("indent", 2)
    with open(fname, "r") as f:
        d = json.load(f)
    d = preprocess(d, pp)
    out_fname = f"__{fname}"
    with open(out_fname, "w") as f:
        json.dump(d, f, **kwargs)
    d["fname"] = str(Path(out_fname).absolute())

    return d

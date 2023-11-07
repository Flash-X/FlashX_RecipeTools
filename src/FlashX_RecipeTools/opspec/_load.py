import json
from ._preprocessor import preprocess


def load(fname, pp):
    with open(fname, "r") as f:
        d = json.load(f)
        preprocess(d, pp)
    return d


def dump(d, fname, **kwargs):
    with open(fname, "w") as f:
        json.dump(d, f, **kwargs)

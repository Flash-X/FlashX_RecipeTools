import json
import re

PP_REGEX = re.compile("\{\S*?\}")
EVAL_REGEX = re.compile("\{(?P<val>[-.0-9+*]+)\}")
PP = {
    "NDIM": 2,
    "NXB": 16,
    "NYB": 16,
    "NZB": 1,
    "NGUARD": 4,
    "K1D": 1,
    "K2D": 1,
    "K3D": 0,
    "NFLUXES": 5,
    "DENS_VAR": 1,
    "PRES_VAR": 2,
    "VELX_VAR": 3,
    "VELY_VAR": 4,
    "VELZ_VAR": 5,
    "ENER_VAR": 6,
    "EINT_VAR": 7,
    "TEMP_VAR": 8,
    "GAMC_VAR": 9,
}

def _str2int(v):
    """
    try to convert string to integers
    """
    if isinstance(v, list):
        vList = []
        for _v in v:
            vList.append(_str2int(_v))
        return vList
    assert isinstance(v, str), type(v)
    try:
        v = int(v)
    except ValueError:
        pass
    return v


def _eval_pp(v):
    """
    find {PP} in a given string and replace it to eval(PP)
    """
    if isinstance(v, list):
        vList = []
        for _v in v:
            vList.append(_eval_pp(_v))
        return vList
    assert isinstance(v, str), type(v)
    return re.sub(EVAL_REGEX, lambda m: str(eval(m.group("val"))), v)


def _replace_pp(v):
    """
    find and replace defind in PP
    """
    if isinstance(v, list):
        vList = []
        for _v in v:
            vList.append(_replace_pp(_v))
        return vList

    assert isinstance(v, str), type(v)

    for pp_k, pp_v in PP.items():
        v = v.replace(pp_k, str(pp_v))

    return v


def _find_pp(v):
    """
    check if a given string has "{PP}"
    """
    if isinstance(v, list):
        for _v in v:
            if _find_pp(_v):
                return True
    elif isinstance(v, str):
        if re.search(PP_REGEX, v):
            return True
    else:
        return False
    return False


def opspec_pp(d):
    assert isinstance(d, dict), type(d)

    for k, v in d.items():
        if isinstance(v, dict):
            opspec_pp(v)
        else:
            if _find_pp(v):
                # print("[before]", d[k])
                v = _replace_pp(v)
                v = _eval_pp(v)
                v = _str2int(v)
                d[k] = v
                # print("[after]", d[k])


def _load():
    op_spec_fname = "operation_spec.json"
    with open(op_spec_fname) as f:
        d = json.load(f)
    return d


def main():

    d = _load()
    opspec_pp(d)

    return d



if __name__ == "__main__":

    d = main()
    print(d)


import re

PP_REGEX = re.compile("\{\S*?\}")
EVAL_REGEX = re.compile("\{(?P<val>[-.0-9+*]+)\}")


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


def _replace_pp(v, pp):
    """
    find and replace defind in pp
    """
    if isinstance(v, list):
        vList = []
        for _v in v:
            vList.append(_replace_pp(_v, pp))
        return vList

    assert isinstance(v, str), type(v)
    assert isinstance(pp, dict), type(pp)

    for pp_k, pp_v in pp.items():
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


def preprocess(opspec:dict, pp:dict) -> dict:

    d = dict()

    for k, v in opspec.items():
        if isinstance(v, dict):
            d[k] = preprocess(v, pp)
        else:
            if _find_pp(v):
                v = _replace_pp(v, pp)
                v = _eval_pp(v)
                v = _str2int(v)
            d[k] = v

    return d

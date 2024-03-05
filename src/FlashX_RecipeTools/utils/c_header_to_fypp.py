import re
from pathlib import Path

COMMENTS = re.compile(r"(!|\/\*|\/\/).+")
INCLUDE = re.compile(r"(#include)\s+(?P<fname>\S+)")
TOKEN = re.compile(r"#(?P<token>\S+)")
DEFINE = re.compile(r"(#define)\s+(?P<varname>[^\(\)\r\n\t\f\v ]+)\s+(?P<value>.+)")
IFDEF = re.compile(r"(#ifdef)\s+(?P<varname>\S+)")
IFNDEF = re.compile(r"(#ifndef)\s+(?P<varname>\S+)")


def _delete_double_underscores(varname):
    return varname.replace("__", "")


def _process_token_only(token, line, replace_with=""):

    pattern_re = re.compile(f"(#)(?P<token>{token})")

    _token = token
    if replace_with:
        _token = replace_with
    return re.sub(pattern_re, f"#:{_token}", line)


def _process_define(line):

    match = re.match(DEFINE, line)

    if not match:
        define_without_value = re.match(re.compile(r"(#define)\s+(?P<varname>[^\(\)\r\n\t\f\v ]+)"), line)
        if define_without_value:
            varname = define_without_value.group("varname")
            varname = _delete_double_underscores(varname)
            return f"#:set {varname}"
        return ""

    varname = match.group("varname")
    varname = _delete_double_underscores(varname)
    value = match.group("value") if match.group("value") else 1

    return f"#:set {varname}={value}"


def _process_include(line):

    match = re.match(INCLUDE, line)
    fname = match.group("fname")
    fname_fypp = re.sub(r".h", r".fypp", fname)

    return f"#:include {fname_fypp}"


def _process_ifdef(line):

    match = re.match(IFDEF, line)
    varname = match.group("varname")
    varname = _delete_double_underscores(varname)

    return f"#:if defined('{varname}')"


def _process_ifndef(line):

    match = re.match(IFNDEF, line)
    varname = match.group("varname")
    varname = _delete_double_underscores(varname)

    return f"#:if not defined('{varname}')"


def _processline(token, line):

    _line = ""
    if token.lower() == "define":
        _line = _process_define(line)
    elif token.lower() == "include":
        _line = _process_include(line)
    elif token.lower() == "ifdef":
        _line = _process_ifdef(line)
    elif token.lower() == "ifndef":
        _line = _process_ifndef(line)
    elif token.lower() in ["if", "else", "elif", "endif"]:
        _line = _process_token_only(token, line)

    return _line


def c_header_to_fypp(fname):
    """
    Reads C header file and write to fypp header file
    with the same name and same path
    """

    fname = Path(fname)
    if not fname.is_file():
        raise ValueError(f"{fname} is not a file")
    if not fname.suffix == ".h":
        raise ValueError(f"{fname} has not a valid extension")

    # delte comments
    with open(fname, "r") as f:
        raw = f.read()
    raw = re.sub(COMMENTS, "", raw)

    # processing lines
    out_lines = []
    in_comment = False
    for line in raw.splitlines():

        # dealing comments block
        if in_comment and line.strip() == "#endif":
            out_lines.append("#:endif")
            in_comment = False
            continue
        if in_comment:
            out_lines.append(line)
            continue
        if line.strip() == "#if 0":
            out_lines.append("#:if 0")
            in_comment = True
            continue

        match = re.match(TOKEN, line)
        if match:
            fypp_line = _processline(match.group("token"), line)
            out_lines.append(fypp_line)

    # write to a file
    out_fname = Path(fname).with_suffix(".fypp").absolute()
    with open(out_fname, "w") as f:
        for line in out_lines:
            f.write(line + "\n")

    return

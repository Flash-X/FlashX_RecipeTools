"""
A list of constants that contain keywords for parsing milhoja directives.
"""
from collections import OrderedDict

# DIRECTIVE SYMBOLS
DIRECTIVE_LINE = "!$"
BEGIN = "begin"
END = "end"
COMMON = "common"
SUBROUTINE = "subroutine"
CONTINUE = "&"
MILHOJA = "milhoja"

# VARIABLE SYMBOLS
RW_SYMBOLS = {"R", "W", "RW"}
EXTENTS = "extents"
DTYPE = "type"
SOURCE = "source"
LBOUND = "lbound"

# Operation Specification Template
OP_SPEC_TEMPLATE = {
    "format": ["Milhoja-JSON", "1.0.0"],
    "name": "",
    "variable_index_base": 1,
    "__includes": [],
    "external": {},
    "scratch": {}

    # functions go here.
}

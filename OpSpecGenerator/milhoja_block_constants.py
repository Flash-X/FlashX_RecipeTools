"""
A list of constants that contain keywords for parsing milhoja directives.
"""

# DIRECTIVE SYMBOLS
DIRECTIVE_LINE = "!$"
BEGIN = "begin"
END = "end"
COMMON = "common"
MACRO = "macro"
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
    "variable_index_base": 0,
    "__includes": [],
    "external": {},
    "scratch": {}

    # functions go here.
}

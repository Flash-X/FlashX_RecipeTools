"""
A list of constants that contain keywords for parsing milhoja directives.
"""
import operator

from collections import OrderedDict

# PARSING CONSTANTS
MAX_RANGE_LENGTH = 1000
# for ensuring that a given r/w/rw range consists only of numeric values and parenthesis.
RANGE_REGEX = r'[\(\)\+\-\*\/\d\ ]*'

# DIRECTIVE SYMBOLS
DIRECTIVE_LINE = "!!"
BEGIN = "begin"
END = "end"
COMMON = "common"
SUBROUTINE = "subroutine"
CONTINUE = "&"
MILHOJA = "milhoja"

# VARIABLE SYMBOLS
READ = "R"
WRITE = "W"
READWRITE = "RW"
RW_SYMBOLS = {READ, WRITE, READWRITE}
EXTENTS = "extents"
DTYPE = "type"
SOURCE = "source"
LBOUND = "lbound"

# Operation Specification Template
OP_SPEC_TEMPLATE = {
    "format": ["Milhoja-JSON", "1.0.0"],
    "name": "",
    "variable_index_base": 1,
    "external": {},
    "scratch": {}

    # functions go here.
}

# OPERATORS FOR MATH PARSING
OPERATIONS = {
    '+': {
        "priority": 1,
        "side": 'L',
        "function": operator.add
    },
    '-': {
        "priority": 1,
        "side": 'L',
        "function": operator.sub
    },
    '*': {
        "priority": 2,
        "side": 'L', 
        "function": operator.mul
    },
    '/': {
        "priority": 2,
        "side": 'L',
        "function": operator.floordiv  # no floats!
    },
    '**': {
        "priority": 3,
        "side": 'R',
        "function": operator.pow
    }
}

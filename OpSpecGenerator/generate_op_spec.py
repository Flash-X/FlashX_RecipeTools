#!/usr/bin/env python3
# TODO: Replace magic strings with predefined dict keys found in Milhoja pypackage.

import json
import argparse
import os
import re
import subprocess
import milhoja
import milhoja_block_constants as mbc
import sys

from copy import deepcopy
from pathlib import Path

# def _get_variable_information(macros: dict, line: str, tile_only: bool) -> VariableInformation:
#     if line.startswith('!!'):
#         line = line.replace('!!', '', 1)
#     line = replace_constants_in_line(line)
#     line = line.replace(' ', '')
#     declaration_and_name = line.split("::")
#     declaration = declaration_and_name[0]
#     names_and_sizes = declaration_and_name[1].split('!!')
#     names = names_and_sizes[0].split(',')
#     names = [ 
#         name.replace(':', '').replace(',', '').replace('()', '')[: name.index('=') if '=' in name else None ]
#         for name in names 
#     ]

#     size_eq = []
#     start1 = ""
#     start2 = ""
#     end1 = ""
#     end2 = ""
#     if len(names_and_sizes) > 1 and tile_only:
#         size_eq = [ '(' + names_and_sizes[1].split('=')[1] + ')' ]
#     elif tile_only: 
#         if "dimension" in declaration:
#             use_unk_equation = False
#             size_eq = declaration[ declaration.index('(')+1:declaration.index(')') ].split(',')
#             size_eq = [ f'({eq})' for eq in size_eq ]
#             try:
#                 for idx,eq in enumerate(size_eq):
#                     low_hi = eq.replace('(', '').replace(')', '').split(':')
#                     low_hi = [item for item in low_hi if item != '']
#                     if len(low_hi) > 1:
#                         use_unk_equation = False
#                         total = abs(int(low_hi[0])) + abs(int(low_hi[1]))
#                         size_eq[idx] = f'({total})'
#                     contains_numeric = r'[1-9]+'
#                     values = re.findall(contains_numeric, eq)
#                     if not values:
#                         use_unk_equation = True
#                     else:
#                         use_unk_equation = False                  
#             except:
#                 print(f"Constant value not found when processing {size_eq}") 

#             if use_unk_equation:
#                 eq = macro_util.replace_macro_value_with_constant(macros, _UNK_EQUATION)
#                 size_eq = eq.split('~')
#                 start1 = "0"
#                 start2 = "0"
#                 # Default values for start and end in an unk array. TODO: Add identifier for number of unknowns?
#                 end1 = macro_util.replace_macro_value_with_constant(macros, "NUNK_VARS - 1")
#                 end2 = macro_util.replace_macro_value_with_constant(macros, "NUNK_VARS - 1")

#     if not size_eq and tile_only:
#         raise BaseException(f"[{line}] Array missing dimensions.")
    
#     declaration = declaration.split(',')
#     vinfo = VariableInformation(names, _F_DATATYPES[declaration[0]], size_eq, start1, end1, start2, end2)
#     return vinfo


# def replace_constants_in_line(line: str):
#     """Replaces all constants in a line with their derived macros."""
#     formatted_line = line
#     for constant,value in derived_constants.items():
#         formatted_line = formatted_line.replace(constant, value)
#     return formatted_line 
        

# def _derived_constants(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
#     """Parses the derived constants."""
#     if start:
#         print(f'Parsing {_DERIVED}')
#     else:
#         line = line.replace('!!', '').rstrip().lstrip()
#         kv = line.split(' ', 1)
#         kv[1] = kv[1].replace('^', '**')
#         # TODO: This is reaLLy really bad. I need to be absolutely certain that a user cannot insert malicious python code
#         #       since this is being executed. I can probably check if the equation does not contain any alphabetic characters?
#         derived_constants[kv[0]] = str(eval(kv[1]))


# def _parse_ood(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
#     # print(f'Parsing {_OOD}')
#     if not start:
#         vinfo = _get_variable_information(macros, line, tile)
#         JSON['tile_scratch'] = { 
#             **JSON['tile_scratch'], 
#             **{ 
#                 name: {
#                     'type': vinfo.dtype, 
#                     'extents': vinfo.size_equation
#                 } for name in vinfo.names 
#             } 
#         }
def __create_op_spec_json(lines, intf_name, op_name, debug) -> dict:
    js = deepcopy(mbc.OP_SPEC_TEMPLATE)
    js["name"] = op_name

    block_stack = []  # realistically the block stack will not be larger than 1.
    for line in lines:
        # update the block stack based on the statement
        if line.startswith(mbc.DIRECTIVE_LINE + mbc.MILHOJA):
            tokens = line.lower().split(" ")
            if tokens[1] == mbc.BEGIN:
                block_stack.append(tokens[2])
            elif tokens[1] == mbc.END:
                if block_stack[-1] != tokens[2]:
                    print(f"Unexpected block statement type {tokens[2]}")
                    exit(-1)
                block_stack.pop()
            else:
                print(f"Unrecognized statement {tokens[1]}")
            continue

        if debug and block_stack:
            print(f"Current block: {block_stack[-1]}")

        if block_stack:
            current = block_stack[-1]

    return js


def __get_all_interface_lines(fptr, debug) -> list:
    milhoja_block_stack = []
    lines = []
    full_line = ""
    # todo:: call strip() less times

    # for each line in the file...
    for line in fptr:
        # check if we need to add to line stack
        # Controls whether or not we add to the list of lines via a stack.
        # We discard anything outside of a milhoja directive block.
        if line.strip().startswith(mbc.DIRECTIVE_LINE):
            check_directive = line.replace(" ", "").lower()
            # this checks if its even a milhoja directive.
            if check_directive.startswith(mbc.DIRECTIVE_LINE + mbc.MILHOJA):
                if mbc.BEGIN in check_directive:
                    milhoja_block_stack.append(None)
                elif mbc.END in check_directive:
                    try:
                        milhoja_block_stack.pop()
                    except:
                        print(f"Missing start or end block statement. Line: {line}")
                        exit(-1)
                assert len(line.strip().split(' ')) == 3, "Missing whitespace in directive statement."
                lines.append(line.strip())
                continue

        # ignore lines if the stack is empty or if the line is empty
        if not milhoja_block_stack or not line.strip():
            continue

        if full_line:
            line = line.strip()[len(mbc.DIRECTIVE_LINE):].strip()

        line = line.strip()
        if line.endswith(mbc.CONTINUE):
            line = line[:-(len(mbc.CONTINUE))]
            full_line += line
            continue

        full_line += line
        lines.append(full_line)
        full_line = ""

    # check to make sure that every begin block has an end statement.
    assert not milhoja_block_stack, "Block stack is not empty."
    return lines


def __process_interface_file(name: str, file: Path, debug: bool) -> dict:
    """
    Process an interface file and return a filled dictionary.
    """
    lines = []
    # get all lines that are relevent to the op spec (AKA milhoja blocks.)
    with open(file, 'r') as fptr:
        lines = __get_all_interface_lines(fptr, debug)

    if debug:
        for line in lines:
            print(line)

    interface_name = os.path.basename(file)
    opspec = __create_op_spec_json(lines, interface_name, name, debug)
    return opspec


def __dump_to_json(dictionary: dict, file_path: Path):
    """Dumps a *dictionary* to a json file based on *name*."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, ensure_ascii=False, indent=4)


def generate_op_spec(name: str, interface_file, debug: bool):
    """
    Process the interface file to create the op specification.
    Assumes that the file has been run through the C preprocessor if
    necessary and that the appropriate setup has been done for determining
    macros. 

    :param str name: The name of the op spec.
    :param str interface_file: The path to the interface file.
    """
    # get interface path
    interface_path = Path(interface_file).resolve()

    # print path info
    if debug:
        print("Processing: ", str(interface_path))

    # create output spec path
    op_spec_path = Path(os.path.dirname(interface_path), name + ".json").resolve()

    # call C++ preprocessor?

    # process file
    op_spec = __process_interface_file(name, interface_path, debug)
    __dump_to_json(op_spec, op_spec_path)

    # then process the data module, so no need to do basic replacing myself.
    # r = subprocess.run(['cpp', '-E', module, processed])
    # if r.returncode != 0:
    #     print( '[JSON Generator] File preprocessing failed.')
    #     print(f'                 path: {module}')

    # datapacket_json = _parse_data_module(processed, tinfo, macro_dict)
    # _dump_to_json(datapacket_json, name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a DataPacket JSON file from a Flash-X data module.")
    parser.add_argument("interface", help="The data module file to generate a DataPacket JSON from.")
    parser.add_argument("--name", "-n", help="The name of the DataPacket JSON output.")
    parser.add_argument("--debug", "-d", action="store_true", help="Print debug output.")
    args = parser.parse_args()

    if not args.name:
        print("Operation Specification requires a name.")
        exit(-1)

    if not args.interface:
        print("No interface provided.")
        exit(-1)

    generate_op_spec(args.name, args.interface, args.debug)
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


# def _parse_htd(macros: dict, line: str, start: bool, JSON: dict, tile_only: bool):
#     # print(f'Parsing {_HTD}')
#     if not start:
#         vinfo = _get_variable_information(macros, line, tile_only)
#         if tile_only:
#             JSON['tile_in'] = { 
#                 **JSON['tile_in'], 
#                 **{ name: 
#                     {'type': vinfo.dtype, 
#                      'extents': vinfo.size_equation,
#                      'start': vinfo.start1,
#                      'end': vinfo.end1,
#                     } for name in vinfo.names } 
#             }
#         else:
#             JSON['constructor'] = { 
#                 **JSON['constructor'], 
#                 **{ name: vinfo.dtype for name in vinfo.names} 
#             }


# def _parse_both(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
#     # print(f'Parsing {_BOTH}')
#     if not start:
#         vinfo = _get_variable_information(macros, line, tile)
#         JSON['tile_in_out'] = { 
#             **JSON['tile_in_out'], 
#             **{ name: 
#                 {'type': vinfo.dtype, 
#                  'extents': vinfo.size_equation,
#                 #  TODO: how to insert default variable masking from existing information? Can potentially 
#                  'start_in': vinfo.start1,
#                  'start_out': vinfo.start2,
#                  'end_in': vinfo.end1,
#                  'end_out': vinfo.end2
#                 } for name in vinfo.names 
#             } 
#         }

def __get_all_interface_lines(fptr, debug) -> list:
    milhoja_block_stack = []
    lines = []
    full_line = ""

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
                lines.append(line.strip())
                continue

        # ignore lines if the stack is empty
        if not milhoja_block_stack or not line:
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


def __process_interface_file(file: Path, debug: bool) -> dict:
    """
    Process an interface file and return a filled dictionary.
    """
    lines = []
    with open(file, 'r') as fptr:
        lines = __get_all_interface_lines(fptr, debug)

    if debug:
        for line in lines:
            print(line)

    opspec = deepcopy(mbc.OP_SPEC_TEMPLATE)
    for line in lines:
        ...

    return opspec


def _dump_to_json(dictionary: dict, file_path: Path):
    """Dumps a *dictionary* to a json file based on *name*."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, ensure_ascii=False, indent=4)


def generate_op_spec(name: str, interface_file, debug: bool):
    """
    Main driver function to parse data module. Assumes that the data module as well as constants defined in the data module are
    contained within the same directory.

    :param str name: The name of the output file.
    :param str tinfo: The name of the task function information file.
    :param str module: The path to the data module to parse.
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
    op_spec = __process_interface_file(interface_path, debug)

    # processed = module + '.jsonpreprocessed'
    # use c preprocessor to get macros.
    # macros = f'{name}.macros'
    # r = subprocess.run(['cpp', '-dM', '-o', macros, module])
    # if r.returncode != 0:
    #     print( '[JSON Generator] Failed to get macros.')
    #     print(f'                 path: {module}')
    # macro_dict = macro_util.parse_macros_file(macros)

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
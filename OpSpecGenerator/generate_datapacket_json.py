#!/usr/bin/env python3

# TODO: Replace magic strings with predefined dict keys found in Milhoja pypackage.

import json
import argparse
import re
import subprocess
from fx_datapacket_json_generator import macro_utility as macro_util
from fx_datapacket_json_generator import macro_names as keywords
from dataclasses import dataclass

_ERR_NO_DATA_MODULE = -1
_ERR_NO_TINFO = -2
_ERR_NO_NAME = -3

# Parsing keywords
_CONSTANTS_FROM = 'constants from'
_IGNORE = 'TO BE IGNORED'
_BOTH = 'BOTHWAYS'
_HTD = 'FROMHOSTTODEVICEONLY'
_OOD = 'ONLYONDEVICE'
_DERIVED = 'derived constants'
_TILE = 'TILEPRIVATE'
_GLOBAL = 'GLOBAL'

_KEYWORDS = {
    _OOD,
    _HTD,
    _BOTH,
    _IGNORE,
    _DERIVED
}

_F_DATATYPES = {
    'logical': 'bool',
    'integer': 'int',
    'real': 'real'
}
    
derived_constants = {

}

_JSON_TEMPLATE = {
    "format": ["Milhoja-JSON", "1.0.0"],
    "task_function": {
        "name": "",
        "language": "Fortran",
        "processor": "GPU",
        "cpp_header": "",
        "cpp_source": "",
        "c2f_source": "",
        "fortran_source": "",
        "argument_list": [],
        "argument_specifications": {},
        "subroutine_call_stack": []
    },
    "data_item": {
        "type": "DataPacket",
        "byte_alignment": 16,
        "header": "",
        "source": ""
    }
}
    
_UNK_EQUATION = "(GRID_IHI_GC)~(GRID_JHI_GC)~(GRID_KHI_GC)"
    

@dataclass
class VariableInformation:
    """Struct containing information from the passed in data module."""
    names: list
    dtype: str
    size_equation: list
    start1: str
    end1: str
    start2: str
    end2: str


def _get_variable_information(macros: dict, line: str, tile_only: bool) -> VariableInformation:
    if line.startswith('!!'):
        line = line.replace('!!', '', 1)
    line = replace_constants_in_line(line)
    line = line.replace(' ', '')
    declaration_and_name = line.split("::")
    declaration = declaration_and_name[0]
    names_and_sizes = declaration_and_name[1].split('!!')
    names = names_and_sizes[0].split(',')
    names = [ 
        name.replace(':', '').replace(',', '').replace('()', '')[: name.index('=') if '=' in name else None ]
        for name in names 
    ]

    size_eq = []
    start1 = ""
    start2 = ""
    end1 = ""
    end2 = ""
    if len(names_and_sizes) > 1 and tile_only:
        size_eq = [ '(' + names_and_sizes[1].split('=')[1] + ')' ]
    elif tile_only: 
        if "dimension" in declaration:
            use_unk_equation = False
            size_eq = declaration[ declaration.index('(')+1:declaration.index(')') ].split(',')
            size_eq = [ f'({eq})' for eq in size_eq ]
            try:
                for idx,eq in enumerate(size_eq):
                    low_hi = eq.replace('(', '').replace(')', '').split(':')
                    low_hi = [item for item in low_hi if item != '']
                    if len(low_hi) > 1:
                        use_unk_equation = False
                        total = abs(int(low_hi[0])) + abs(int(low_hi[1]))
                        size_eq[idx] = f'({total})'
                    contains_numeric = r'[1-9]+'
                    values = re.findall(contains_numeric, eq)
                    if not values:
                        use_unk_equation = True
                    else:
                        use_unk_equation = False                  
            except:
                print(f"Constant value not found when processing {size_eq}") 

            if use_unk_equation:
                eq = macro_util.replace_macro_value_with_constant(macros, _UNK_EQUATION)
                size_eq = eq.split('~')
                start1 = "0"
                start2 = "0"
                # Default values for start and end in an unk array. TODO: Add identifier for number of unknowns?
                end1 = macro_util.replace_macro_value_with_constant(macros, "NUNK_VARS - 1")
                end2 = macro_util.replace_macro_value_with_constant(macros, "NUNK_VARS - 1")

    if not size_eq and tile_only:
        raise BaseException(f"[{line}] Array missing dimensions.")
    
    declaration = declaration.split(',')
    vinfo = VariableInformation(names, _F_DATATYPES[declaration[0]], size_eq, start1, end1, start2, end2)
    return vinfo


def _parse_line(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
    return


def replace_constants_in_line(line: str):
    """Replaces all constants in a line with their derived macros."""
    formatted_line = line
    for constant,value in derived_constants.items():
        formatted_line = formatted_line.replace(constant, value)
    return formatted_line 
        

def _derived_constants(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
    """Parses the derived constants."""
    if start:
        print(f'Parsing {_DERIVED}')
    else:
        line = line.replace('!!', '').rstrip().lstrip()
        kv = line.split(' ', 1)
        kv[1] = kv[1].replace('^', '**')
        # TODO: This is reaLLy really bad. I need to be absolutely certain that a user cannot insert malicious python code
        #       since this is being executed. I can probably check if the equation does not contain any alphabetic characters?
        derived_constants[kv[0]] = str(eval(kv[1]))


def _parse_ood(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
    # print(f'Parsing {_OOD}')
    if not start:
        vinfo = _get_variable_information(macros, line, tile)
        JSON['tile_scratch'] = { 
            **JSON['tile_scratch'], 
            **{ 
                name: {
                    'type': vinfo.dtype, 
                    'extents': vinfo.size_equation
                } for name in vinfo.names 
            } 
        }


def _parse_htd(macros: dict, line: str, start: bool, JSON: dict, tile_only: bool):
    # print(f'Parsing {_HTD}')
    if not start:
        vinfo = _get_variable_information(macros, line, tile_only)
        if tile_only:
            JSON['tile_in'] = { 
                **JSON['tile_in'], 
                **{ name: 
                    {'type': vinfo.dtype, 
                     'extents': vinfo.size_equation,
                     'start': vinfo.start1,
                     'end': vinfo.end1,
                    } for name in vinfo.names } 
            }
        else:
            JSON['constructor'] = { 
                **JSON['constructor'], 
                **{ name: vinfo.dtype for name in vinfo.names} 
            }


def _parse_both(macros: dict, line: str, start: bool, JSON: dict, tile: bool):
    # print(f'Parsing {_BOTH}')
    if not start:
        vinfo = _get_variable_information(macros, line, tile)
        JSON['tile_in_out'] = { 
            **JSON['tile_in_out'], 
            **{ name: 
                {'type': vinfo.dtype, 
                 'extents': vinfo.size_equation,
                #  TODO: how to insert default variable masking from existing information? Can potentially 
                 'start_in': vinfo.start1,
                 'start_out': vinfo.start2,
                 'end_in': vinfo.end1,
                 'end_out': vinfo.end2
                } for name in vinfo.names 
            } 
        }


def _dump_to_json(dictionary: dict, name: str) -> str:
    """Dumps a *dictionary* to a json file based on *name*."""
    file_name = f'{name}.json'
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, ensure_ascii=False, indent=4)
    return file_name


def _parse_data_module(path: str, prep_path: str, macros: dict):
    """
    Parses the passed in data module for Flash-X and creates JSON using that information.
    
    :param str path: The path to the data module.
    :param str prep_path: The path to the file containing task function information.
    :param dict macros: The dictionary containing every available macro.
    """
    # Set defaults for datapacket json.
    # Byte align is assumed to come from the sizes json.
    # n_extra_streams is tricky. this needs to come from the task function generator. 
    # task_function_argument_list also needs to come from the task function generator.
    name = "sample"
    args = []
    if prep_path:
        name, args = macro_util.parse_prepGlobal_file(prep_path)
    datapacket_json = {
        "subroutine_name": name,
        "byte_align": 16,
        "n_extra_streams": 0,
        "task_function_argument_list": args,
        "tile_scratch": { },
        "constructor": { },
        "tile_metadata": { },
        "tile_in": { },
        "tile_in_out": { },
        "tile_out": { }
    }

    keyword_func_mapping = {
        _OOD: _parse_ood,
        _HTD: _parse_htd,
        _BOTH: _parse_both,
        _DERIVED: _derived_constants
    }

    with open(path, 'r') as file:
        current_func = _parse_line
        tile_only = True
        for line in file:
            line = line.rstrip().lstrip()
            start = False
            for word in _KEYWORDS:
                if word in line:
                    if word == _IGNORE:
                        return datapacket_json # we're assuming that nothing past this point matters for the data packet.
                    if _TILE in line and word != _CONSTANTS_FROM: tile_only = True
                    elif _GLOBAL in line and word != _CONSTANTS_FROM: tile_only = False
                    current_func = keyword_func_mapping[word]
                    start = True
                    break
            if not line.strip():
                continue
            current_func(macros, line, start, datapacket_json, tile_only)
    return datapacket_json


def main(name: str, tinfo: str, module: str):
    """
    Main driver function to parse data module. Assumes that the data module as well as constants defined in the data module are
    contained within the same directory.

    :param str name: The name of the output file.
    :param str tinfo: The name of the task function information file.
    :param str module: The path to the data module to parse.
    """
    processed = module + '.jsonpreprocessed'
    # use c preprocessor to get macros.
    macros = f'{name}.macros'
    r = subprocess.run(['cpp', '-dM', '-o', macros, module])
    if r.returncode != 0:
        print( '[JSON Generator] Failed to get macros.')
        print(f'                 path: {module}')
    macro_dict = macro_util.parse_macros_file(macros)

    # then process the data module, so no need to do basic replacing myself.
    r = subprocess.run(['cpp', '-E', module, processed])
    if r.returncode != 0:
        print( '[JSON Generator] File preprocessing failed.')
        print(f'                 path: {module}')

    datapacket_json = _parse_data_module(processed, tinfo, macro_dict)
    _dump_to_json(datapacket_json, name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a DataPacket JSON file from a Flash-X data module.")
    parser.add_argument("data_module", help="The data module file to generate a DataPacket JSON from.")
    parser.add_argument("--tinfo", "-t", help="Task function argument information.")
    parser.add_argument("--name", "-n", help="The name of the DataPacket JSON output.")
    args = parser.parse_args()

    if not args.name:
        print("File requires a name.")
        exit(_ERR_NO_NAME)
    # if not args.tinfo:
    #     print("DataPacket JSON requires information about the task function.")
    #     exit(_ERR_NO_TINFO)
    if not args.data_module:
        print("Need Data Module to parse.")
        exit(_ERR_NO_DATA_MODULE)

    main(args.name, args.tinfo, args.data_module)
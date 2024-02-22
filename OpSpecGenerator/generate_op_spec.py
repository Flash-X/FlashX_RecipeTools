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


def __format_structure_index(line) -> list:
    """
    Formats the structure index argument for use by the TaskFunctionAssembler
    """
    line = line[1:-1]
    tokens = [token.strip() for token in line.split(',')]
    return [tokens[0].upper(), int(tokens[1])]


def __split_non_nested(string: str, delim, nest_begin, nest_end, max_splits = -1) -> list:
    """
    Splits a string by commas that are not contained within parenthesis.
    """
    last_idx = 0
    segments = []
    paren_stack = []

    if max_splits == 0:
        return [string]

    # this DOES NOT check for valid parenthesis and bracket placement.
    # When processing lines, this function assumes that the fortran syntax is
    # valid!
    for idx,char in enumerate(string):
        if char in nest_begin:
            paren_stack.append(char)
        elif char in nest_end:
            paren_stack.pop()
        elif char == delim and not paren_stack:
            segments.append(string[last_idx:idx])
            last_idx = idx + 1  # pass the comma
            if last_idx >= len(string) or max_splits > -1 and max_splits < idx:
                break
    # return whole string if could not be split
    if not segments:
        segments.append(string)
    else:
        # append last segment
        segments.append(string[last_idx:])
    return segments


def __get_directive_tokens(line, debug):
    """
    Parses a milhoja directive line and returns the name
    and all associated data with a name.
    """
    token_dict = {}
    tokens = line[len(mbc.DIRECTIVE_LINE):].split("::")
    assert len(tokens) == 2, f"Bad line: {line}"
    name = tokens[0].strip()
    attrs = __split_non_nested(
        tokens[1].strip(),
        delim=',',
        nest_begin=['[', '('],
        nest_end=[')', ']']
    )

    # go through each attribute
    for attribute in attrs:
        attribute = attribute.strip()
        kv = [a.strip() for a in attribute.split('=')]
        assert len(kv) == 2, f"Invalid line: {line}"
        kv[1] = kv[1].replace("[", "(").replace("]", ")")
        token_dict[kv[0]] = kv[1]

    if debug:
        print(
            "Name:", name + "\n",
            "attrs:", token_dict, "\n"
        )

    return name, token_dict


def __create_op_spec_json(lines, intf_name, op_name, debug) -> dict:
    """
    Create the operation specification json from the list of milhoja directive lines.
    Does not support nested blocks.
    """
    common_defs = {}
    sbr_defs = {}
    js = deepcopy(mbc.OP_SPEC_TEMPLATE)
    js["name"] = op_name

    current_subroutine = ""
    current_routine_dict = {}
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
                sbr_defs = {}
            else:
                print(f"Unrecognized statement {tokens[1]}")
            continue

        if block_stack:
            current = block_stack[-1]
            in_common = current.lower() == mbc.COMMON
            # line is a milhoja directive so we process in a specific way.
            if line.startswith(mbc.DIRECTIVE_LINE):
                name,tokens = __get_directive_tokens(line, debug)
                if in_common:
                    assert name not in common_defs, f"{name} defined twice."
                    common_defs[name] = tokens

                    # format structure index
                    if "structure_index" in common_defs[name]:
                        idx = common_defs[name]["structure_index"]
                        idx = __format_structure_index(idx)
                        common_defs[name]["structure_index"] = idx

                    # special check to 
                    if tokens["source"] in {"external", "scratch"}:
                        if mbc.EXTENTS not in tokens:
                            tokens["extents"] = "()"
                        js[tokens["source"]][name] = tokens

                else:
                    # need to determine the function we are in
                    assert name not in sbr_defs, f"{name} defined twice."
                    if mbc.COMMON in tokens:
                        common_def = common_defs[tokens[mbc.COMMON]]
                        if common_def["source"] in {"external", "scratch"}:
                            tokens = {"source": common_def["source"], "name": tokens[mbc.COMMON]}
                        else:
                            tokens = common_def
                    sbr_defs[name] = tokens

            # line is not a milhoja directive
            else:
                # check if line starts with a subroutine def
                if line.startswith("subroutine"):
                    routine_info_regex = r"\w+\(.*\)"
                    info = re.findall(routine_info_regex, line)[0]
                    arg_start = info.find("(")
                    name = info[:arg_start]
                    args = [arg.strip() for arg in info[arg_start+1:-1].split(',')]

                    # here we assume that the subroutine argument list is complete.
                    js[name] = {}
                    js[name]["interface_file"] = intf_name
                    js[name]["argument_list"] = args
                    js[name].update(sbr_defs)

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
            pcs = line.strip()
            start = len(mbc.DIRECTIVE_LINE) if pcs.startswith(mbc.DIRECTIVE_LINE) else 0
            line = pcs[start:].strip()

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


def __process_interface_file(name: str, file: Path, interface_name, debug: bool) -> dict:
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

    opspec = __create_op_spec_json(lines, interface_name, name, debug)
    return opspec


def __dump_to_json(dictionary: dict, file_path: Path):
    """Dumps a *dictionary* to a json file based on *name*."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, ensure_ascii=False, indent=4)


def generate_op_spec(name: str, interface_file, debug=False, call_cpp=False):
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
    if_name = os.path.basename(interface_path)

    # print path info
    if debug:
        print("Processing: ", str(interface_path))

    # create output spec path
    op_spec_path = Path(os.path.dirname(interface_path), name + ".json").resolve()

    # call C++ preprocessor?
    if call_cpp:
        base = "_pp_" + os.path.basename(interface_path)
        preproc_file = Path(os.path.dirname(interface_path), base)
        result = subprocess.check_output(f'cpp -E -P {str(interface_path)} {preproc_file}; exit 0', shell=True)
        if result:
            print(result)
            exit(-1)
        interface_path = preproc_file

    # process file
    op_spec = __process_interface_file(name, interface_path, if_name, debug)
    __dump_to_json(op_spec, op_spec_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a DataPacket JSON file from a Flash-X data module.")
    parser.add_argument("interface", help="The data module file to generate a DataPacket JSON from.")
    parser.add_argument("--name", "-n", help="The name of the DataPacket JSON output.")
    parser.add_argument("--cpp", "-c", action="store_true", help="Calls the C preprocessor on the interface file before processing.")
    parser.add_argument("--debug", "-d", action="store_true", help="Print debug output.")
    args = parser.parse_args()

    if not args.name:
        print("Operation Specification requires a name.")
        exit(-1)

    if not args.interface:
        print("No interface provided.")
        exit(-1)

    generate_op_spec(args.name, args.interface, args.debug, args.cpp)
#!/usr/bin/env python3
# TODO: Replace magic strings with predefined dict keys found in Milhoja pypackage.

import json
import argparse
import os
import re
import subprocess

from loguru import logger
from copy import deepcopy
from pathlib import Path
from warnings import warn
from typing import Tuple,List
from fparser.two.parser import ParserFactory
from fparser.common.readfortran import FortranStringReader
from fparser.two.Fortran2003 import Type_Declaration_Stmt
from fparser.two.Fortran2003 import Subroutine_Stmt
from fparser.common.sourceinfo import FortranFormat

from . import milhoja_block_constants as mbc


def evaluate_simple_expression(line: str) -> int:
    """
    Evaluates simple math expressions, Shunting yard algorithm implementation.
    https://en.wikipedia.org/wiki/Shunting_yard_algorithm

    Can be optimized to reduce -- to + when tokens are parsed
    """
    # get all tokens in expression
    tokens = re.findall(r'\*\*|[\+\-\*\\\(\)]|\d+', line)

    # ensure that all tokens were found by comparing the size of the original
    # string with no spaces to the sum of all token sizes. If the sums are
    # different that means there's an invalid string inside of the extents
    # argument.
    tokens_size = sum([len(token) for token in tokens])
    line_size = len(line.strip().replace(' ', ''))
    if tokens_size != line_size:
        raise Exception(f"Invalid tokens inside of {line}")

    # this should probably be a record or class struct instead of a tuple.
    ops = mbc.OPERATIONS
    op_stack = []
    out_queue = []

    for token in tokens:
        if token.isdigit():
            out_queue.append(int(token))

        elif token in ops:
            if op_stack:
                while op_stack and op_stack[-1] != "(" and \
                (ops[op_stack[-1]]["priority"] > ops[token]["priority"] or \
                (ops[op_stack[-1]]["priority"] == ops[token]["priority"] and \
                ops[token]["side"] == 'L')):
                    out_queue.append(op_stack.pop())
            op_stack.append(token)

        elif token == "(":
            op_stack.append(token)

        elif token == ")":
            while op_stack and op_stack[-1] != "(":
                assert op_stack
                out_queue.append(op_stack.pop())
            assert op_stack[-1] == "("
            op_stack = op_stack[:-1]

    while op_stack:
        top = op_stack.pop()
        assert top != "(", "Invalid statement"
        out_queue.append(top)

    # replace double minus signs with +
    i = 0
    replace = []
    while i < len(out_queue)-1:
        if out_queue[i] == '-' and out_queue[i+1] == '-':
            out_queue[i] = "+"
            del out_queue[i+1]
        i += 1

    running = []
    # next, evaluate the expression held by out_queue.
    for token in out_queue:
        if token in ops:
            op2 = running.pop()
            op1 = running.pop()
            running.append(ops[token]["function"](op1, op2))
        else:
            running.append(token)

    return running[0]


def format_rw_list(line: str) -> list:
    """
    Takes in a list of ranges of the format:
        (x1:x2, y1:y2, z1:z2, ...)
    And processes it to return a list of integers.
    """
    # determine that the input expression is safe by checking input length and
    # ensuring that everything is a numeric value. 
    if len(line) > mbc.MAX_RANGE_LENGTH:
        raise SyntaxError(
            "Range statement is too large for processing. Please simplify.\n"
            f"Statement: {line}"
        )

    # format the expression by removing spaces and outer parens
    if line[0] == "(" and line[-1] == ")":
        line = line[1:-1]
    range_expressions = line.replace(" ", "").split(",")

    # move through each range expression and use ast to parse value
    # if valid.
    rw_range = []
    pattern = re.compile(mbc.RANGE_REGEX)
    for expr in range_expressions:
        # case1: if the expr is given as array range
        if ":" in expr:
            rng = expr.split(":")
            low,high = rng[0],rng[1]
            lo_success = pattern.match(low)
            hi_success = pattern.match(high)

            # if the expressions are valid
            if lo_success and hi_success:
                rng = []
                for ex in [low,high]:
                    rng.append(evaluate_simple_expression(ex))
                rw_range.extend(list(range(rng[0], rng[1]+1)))
            else:
                warn(f"Expression {expr} is not valid. Ignoring.")
        # case2: if the expr is a simple expression of an integer
        else:
            if pattern.match(expr):
                rw_range.append(evaluate_simple_expression(expr))
            else:
                warn(f"Expression {expr} is not valid. Ignoring.")

    return sorted(rw_range)


def __format_structure_index(line: str) -> list:
    """
    Formats the structure index argument for use by the TaskFunctionAssembler.

    :param str line: The line to format.
    :return: The formatted structure index as a list.
    """
    line = line[1:-1]
    tokens = [token.strip() for token in line.split(',')]
    return [tokens[0].upper(), int(tokens[1])]


def __split_non_nested(string: str, delim: str, nest_begin: list, nest_end: list, max_splits = -1) -> list:
    """
    Splits a string by commas that are not contained within parenthesis.

    :param str string: The string to split.
    :param str delim: The delimiter to split by.
    :param list nest_begin: The list of chars that begin a nest.
    :param list nest_end: The list of chars that end a nest.
    :param int max_splits: The number of splits for a string. Default splits entire string.
    :return: The split string.
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


def __get_directive_tokens(line: str, debug: bool) -> Tuple[str, dict]:
    """
    Parses a milhoja directive line and returns the name and all associated data with a name.

    :param str line: The line to parse.
    :param bool debug: Prints debug information if enabled.
    :return: A tuple containing the name and tokens.
    """
    token_dict = {}
    tokens = line[len(mbc.DIRECTIVE_LINE):].split("::")
    assert len(tokens) == 2, f"Bad line: {line}"
    name = tokens[0].strip()
    attrs = __split_non_nested(
        tokens[1].strip(),
        delim=',',
        nest_begin=['[', '(', '{'],
        nest_end=[')', ']', '}']
    )

    # go through each attribute
    for attribute in attrs:
        attribute = attribute.strip()
        kv = [a.strip() for a in attribute.split('=')]
        assert len(kv) == 2, f"Invalid line: {line}"
        kv[1] = kv[1].replace("[", "(").replace("]", ")")
        token_dict[kv[0]] = kv[1]

    if debug:
        logger.info(
            "\n" +
            "Name:   {_name} \n" +
            "attrs:  {_token_dict} \n",
            _name=name,
            _token_dict=token_dict
        )

    return name, token_dict


def __build_section_list(lines: list) -> list:
    """
    Builds a list containing all lines in each section.

    :param list lines: Every milhoja directive line.
    :return: The list containing all sections
    """
    all_blocks = []
    for idx,line in enumerate(lines):
        if "".join(line.split()).startswith(mbc.DIRECTIVE_LINE + mbc.MILHOJA + mbc.BEGIN):
            sub_start = idx
            continue

        if "".join(line.split()).startswith(mbc.DIRECTIVE_LINE + mbc.MILHOJA + mbc.END):
            all_blocks.append(lines[sub_start:idx+1])

    if all_blocks and (not all_blocks[0][0].endswith(mbc.COMMON)):
        raise RuntimeError("Expected `common` section as first section in interface file.")

    return all_blocks


def __adjust_token_keys(tokens: dict) -> dict:
    """
    Adjusts keys and certain values inside of the tokens dict to be lowercase.
    """
    adjusted = {}
    for key in tokens:
        adjusted_key = key.lower()
        adjusted_token = tokens[key]
        if adjusted_key in ["common", "lbound", "type", "extents", "array"]:
            adjusted_token = adjusted_token.lower()
        adjusted[adjusted_key] = adjusted_token
    return adjusted


def __process_annotation_line(line: str, debug: bool) -> Tuple[str, dict]:
    """
    Processes a milhoja annotation line.

    :param str line: The line to process.
    :return: The name of the variable in the line & all associated tokens.
    """
    name,tokens = __get_directive_tokens(line, debug)
    name = name.lower()
    tokens = __adjust_token_keys(tokens)
    for rw_key in mbc.RW_SYMBOLS:
        key = rw_key.lower()
        if key in tokens:
            tokens[key] = format_rw_list(tokens[key])

    # Process extents and update the tokens dictionary.
    exts = tokens.get("extents", "()")
    if exts != "()":
        # extents guaranteed to be surrounded be parens and be comma separated.
        exts = \
            "(" + ','.join([str(evaluate_simple_expression(expr)) for expr in exts[1:-1].split(',')]) + ")"

    if "source" in tokens and tokens["source"] in {"external", "scratch"}:
        tokens["extents"] = exts

    if "origin" in tokens:
        if tokens["source"] != "external":
            msg = "Only external is allowed to have origin field."
            raise ValueError(msg)
        origin_source, origin_name = [w.strip() for w in tokens["origin"].split(':')]
        tokens["application_specific"] = {
            "origin": origin_source.lower(),
            "varname": origin_name.lower(),
        }
        del tokens["origin"]

    return name,tokens


def __process_common_block(lines: list, json: dict, debug: bool) -> dict:
    """
    Processes all lines in a common block.

    :param list lines: All lines in the common block.
    :param dict json: The op spec json to modify.
    :return: A dict of common definitions.
    """
    common_definitions = {}
    lines = lines[1:-1]
    for line in lines:
        name,tokens = __process_annotation_line(line, debug)

        assert name not in common_definitions, f"{name} defined twice."
        common_definitions[name] = tokens

        # format structure index
        if "structure_index" in common_definitions[name]:
            idx = common_definitions[name]["structure_index"]
            idx = __format_structure_index(idx)
            common_definitions[name]["structure_index"] = idx

        if tokens["source"] in {"external", "scratch"}:
            json[tokens["source"]][name] = tokens

    return common_definitions


def __process_subroutine_block(lines: List[str], common_definitions: dict, interface_file: str, debug: bool) -> dict:
    """
    Processes a subroutine block and returns all argument definitions.

    :param List[str] lines: A list of all lines inside a subroutine block.
    :param dict common_definitions: All common_definitions from the common block.
    :param str interface_file: The name of the interface file.
    :return: A dict containing all variable definitions for the subroutine.
    """
    lines = lines[1:-1]  # remove begin & end directives.
    argument_definitions = {}
    subroutine_lines = ""
    for idx,line in enumerate(lines):
        if line.startswith(mbc.DIRECTIVE_LINE):  # parse any annotation lines from the user.
            var_name,tokens = __process_annotation_line(line, debug)
            # need to determine the function we are in
            assert var_name not in argument_definitions, f"{var_name} defined twice."
            if mbc.COMMON in tokens:
                common_def = common_definitions[tokens[mbc.COMMON]]
                if common_def["source"] in {"external", "scratch"}:
                    tokens = {"source": common_def["source"], "name": tokens[mbc.COMMON]}
                else:
                    tokens = common_def
            else:
                assert tokens["source"].lower() != "grid_data", \
                    f"{var_name}, grid_data cannot be local to function."
            argument_definitions[var_name] = tokens

        elif line.startswith('subroutine'):  # parse the subroutine prototype definition
            subroutine_lines = '\n'.join(lines[idx:])

    def parse_tree(child, subroutine_defs, common_defs, sub_data={}):
        # use a dictionary to save any data from the recursive function to avoid
        # complex return cases, due to the need to parse the entire tree.
        if child:
            for sub in child.content:
                if isinstance(sub, Subroutine_Stmt):
                    subr_name = str(sub.get_name())
                    arg_list = str(sub.items[2]).split(', ')
                    sub_data["name"] = subr_name
                    sub_data["arg_list"] = [arg.lower() for arg in arg_list]

                elif isinstance(sub, Type_Declaration_Stmt):
                    dtype = str(sub.items[0]).lower()
                    name_list = str(sub.items[2]).split(', ')
                    name_list = [n[:n.find('(')].lower() if '(' in n else n.lower() for n in name_list]

                    for n in name_list:
                        data = subroutine_defs.get(n.lower(), None)
                        if not data:
                            raise RuntimeError(f"Annotation variable & subroutine dummy arg mismatch ({n}).")

                        if 'name' in data:
                            data = common_defs[data['name']]

                        if data['source'] == 'external' or data['source'] == 'scratch':
                            data['type'] = dtype

                if hasattr(sub, "content"):
                    parse_tree(sub, subroutine_defs, common_definitions, sub_data)


    # parse the fortran lines using fparser
    factory = ParserFactory().create(std='f2003')
    string_reader = FortranStringReader(subroutine_lines)
    string_reader.set_format(FortranFormat(True, True))
    tree = factory(string_reader)
    sub_data = {
        "name": "",
        "arg_list": []
    }
    if tree:
        parse_tree(tree, argument_definitions, common_definitions, sub_data)

    # make sure the argument lists match.
    if set(sub_data["arg_list"]) != set(argument_definitions.keys()):
        raise Exception(
            "Dummy argument definitions missing in milhoja block.\n"
            f"Args: {sub_data['arg_list']}\nDefs:, {list(argument_definitions.keys())}"
        )

    subroutine_data = {
        sub_data["name"]: {
            "interface_file": interface_file,
            "argument_list": sub_data["arg_list"],
            "argument_specifications": argument_definitions
        }
    }
    return subroutine_data


def __create_op_spec_json(lines: list, intf_name: str, op_name: str, debug: bool) -> dict:
    """
    Create the operation specification json from the list of milhoja directive lines.

    :param list lines: All milhoja directive lines.
    :param str intf_name: The name of the interface file.
    :param str op_name: The operation spec name.
    :param bool debug: Print debug information if true.
    :return: Returns the finalized json.
    """
    sbr_defs = {}
    js = deepcopy(mbc.OP_SPEC_TEMPLATE)
    js["name"] = op_name

    sections = __build_section_list(lines)
    # here we assume that the first section found in the list of sections
    # is always common
    commons = __process_common_block(sections[0], js, debug)
    for section in sections[1:]:
        routine_info = __process_subroutine_block(section, commons, intf_name, debug)
        sbr_defs.update(routine_info)

    # move any scratch or external data in a subroutine to the outer 
    for routine in sbr_defs.keys():
        arg_spec = sbr_defs[routine]["argument_specifications"]
        for arg,spec in arg_spec.items():
            # here, we need to check the specific source of the variable
            # to determine if it needs to be moved outside of the 
            # subroutine spec.
            if spec["source"] in {"external", "scratch"} and \
            arg not in js["external"] and arg not in js["scratch"]:
                # identifier = f"_{routine}_{arg}"
                identifier = f"_{arg}"
                # we check if a specific identifier exists and that the variable
                # is not already associated with a specific name.
                if identifier not in js[spec["source"]] and "name" not in spec:
                    var_info = {"source": spec["source"], "name": identifier}
                    js[spec["source"]][identifier] = spec
                    arg_spec[arg] = var_info

    js.update(sbr_defs)
    # clean op spec before returning
    # remove extra information from scratch and external sections
    for shared in {"external", "scratch"}:
        for var in js[shared]:
            del js[shared][var]["source"]

    return js


def __get_all_interface_lines(fptr, debug: bool) -> list:
    """
    Get all interface lines that uses milhoja directives.

    :param fptr: The file pointer pointing to the interface file.
    :param bool debug: If enabled, prints debug information.
    """
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
                        raise Exception(f"Missing start or end block statement. Line: {line}")
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
            logger.info(line)

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
    interface_path = Path(interface_file)
    if_name = os.path.basename(interface_path)

    if not interface_path.is_file():
        raise FileNotFoundError(interface_path)

    # print path info
    if debug:
        logger.info("Processing: ", str(interface_path))

    # create output spec path
    op_spec_path = Path(os.path.dirname(interface_path), "__" + name + "_op_spec.json").resolve()

    # call C++ preprocessor if requested
    if call_cpp:
        base = "__pp_" + os.path.basename(interface_path)
        preproc_file = Path(os.path.dirname(interface_path), base)
        try:
            subprocess.check_output(f'cpp -E -P {str(interface_path)} {preproc_file}', shell=True)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to preprocess a file: {_fname}", _fname=interface_file)
            raise RuntimeError(e)
        interface_path = preproc_file

    # process file
    op_spec = __process_interface_file(name, interface_path, if_name, debug)
    __dump_to_json(op_spec, op_spec_path)
    # delete generated TODO
    if preproc_file is not None:
        preproc_file.unlink()
    return op_spec_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a DataPacket JSON file from a Flash-X data module.")
    parser.add_argument("interface", help="The data module file to generate a DataPacket JSON from.")
    parser.add_argument("--name", "-n", help="The name of the DataPacket JSON output.")
    parser.add_argument("--cpp", "-c", action="store_true", help="Calls the C preprocessor on the interface file before processing.")
    parser.add_argument("--debug", "-d", action="store_true", help="Print debug output.")
    args = parser.parse_args()

    if not args.name:
        raise Exception("Operation Specification requires a name.")

    if not args.interface:
        raise Exception("No interface provided.")

    generate_op_spec(args.name, args.interface, args.debug, args.cpp)

from __future__ import annotations

import re
import json

import milhoja

from typing import TYPE_CHECKING
from pathlib import Path
from loguru import logger

if TYPE_CHECKING:
    from .TimeStepRecipe import TimeStepRecipe

from .construct_partial_tf_spec import construct_partial_tf_spec
from ..utils import MakefileParser


SUPPORTED = {
    "processor": ["gpu", "cpu"],
    "computation_offloading": ["OpenACC"],
    "data_type": ["DataPacket", "TileWrapper"],
}




class TimeStepIR:
    def __init__(self):
        self._flowGraph = None
        self._tf_data_all = None
        self._objdir = None
        self._output_fnames = None
        self._milhoja_path = None
        self._grid_json_path = None

    @property
    def flowGraph(self):
        return self._flowGraph

    @property
    def tf_data_all(self):
        return self._tf_data_all

    @property
    def output_fnames(self):
        return self._output_fnames

    @property
    def objdir(self):
        return self._objdir

    @property
    def milhoja_path(self):
        return self._milhoja_path

    @property
    def grid_json_path(self):
        return self._grid_json_path

    @flowGraph.setter
    def flowGraph(self, value:TimeStepRecipe):
        self._flowGraph = value

    @tf_data_all.setter
    def tf_data_all(self, value:list):
        self._tf_data_all = value

    @output_fnames.setter
    def output_fnames(self, value:set):
        self._output_fnames = value

    @objdir.setter
    def objdir(self, value:Path):
        self._objdir = value

    @milhoja_path.setter
    def milhoja_path(self, value:Path):
        self._milhoja_path = value

    @grid_json_path.setter
    def grid_json_path(self, value:Path):
        self._grid_json_path = value


    def generate_all_codes(self, dest=None) -> None:
        self.objdir = self.flowGraph.objdir
        if dest is None:
            dest = self.objdir

        # gather filenames to be generated from milhoja_pypkg
        self._determine_milhoja_code_fnames()
        # generate __grid.json
        self._generate_grid_json()
        # find a path to Milhoja installation
        self._find_milhoja_path()
        # generate taskfunction and dataitem codes.
        self._generate_milhoja_codes(dest)
        # generate TimeAdvance code
        self._generate_TimeAdvance_code(dest)


    def _determine_milhoja_code_fnames(self) -> None:
        """
        Determines file names to be generated by Milhoja_pypkg,
        check if they are valid, and save it to `self.output_fnames`.
        """
        output_files = set()
        # assuming taskfunction language is Fortran
        for tf_data in self.tf_data_all:
            # get partial task function spec
            partial_tf_spec = construct_partial_tf_spec(tf_data)
            task_function = partial_tf_spec["task_function"]
            data_item = partial_tf_spec["data_item"]

            processor = task_function["processor"]
            offloading = task_function["computation_offloading"] if processor == "gpu" else None
            data_type = data_item["type"]

            # check if the current partial_tf_spec can be processed
            if processor not in SUPPORTED["processor"]:
                raise NotImplementedError(f"Task function for {processor} is not supported yet")
            if offloading and offloading not in SUPPORTED["computation_offloading"]:
                raise NotImplementedError(f"Task function for {offloading} is not supported yet")
            if data_type not in SUPPORTED["data_type"]:
                raise NotImplementedError(f"{data_type} is not supported yet")

            # determine files to be generated
            files_to_be_generated = [
                task_function["cpp_source"],
                task_function["c2f_source"],
                task_function["fortran_source"],
                data_item["header"],
                data_item["module"],
                data_item["source"],
            ]
            for filename in files_to_be_generated:
                # filename must be unique
                if filename in output_files:
                    raise ValueError(f"Duplicate filename detected: {filename}")
                output_files.add(filename)

        self.output_fnames = output_files


    def _find_milhoja_path(self) -> None:
        """
        Find the Milhoja installation path by searching
        "MILHOJA_PATH" macro in the Makefile.h and
        save it to `self.milhoja_path`.
        """
        objdir = self.objdir
        # parse "Makefile" also, in order to resolve macros defined in there. e.g., NDIM
        makefile = MakefileParser([objdir / "Makefile", objdir / "Makefile.h"])
        milhoja_path = makefile.expand_macro("MILHOJA_PATH")

        # if found string is a relative path,
        # assuming it is relative to makefile_site
        # TODO: this is only for test case
        if not Path(milhoja_path).is_absolute():
            self.milhoja_path = objdir / milhoja_path
            return

        if Path(milhoja_path).is_dir():
            self.milhoja_path = milhoja_path
            return

        # if it reaches here, something went wrong
        raise ValueError(f"Unable to resolve the MILHOJA_PATH = {milhoja_path}")


    def _generate_grid_json(self) -> None:
        """
        Reads Simulation.h and write the grid information
        needed for Milhoja to JSON format and save the path for JSON
        to self.grid_json_path.
        """
        simulation_h_path = self.objdir / "Simulation.h"
        grid_json_path = self.objdir / "__grid.json"

        if not simulation_h_path.is_file():
            raise FileNotFoundError(f"{simulation_h_path} is not found in the current directory")
        # the regex pattern to match lines with '#define KEY VALUE'
        pattern = r"^\s*#define\s+(\w+)\s+(\S+)"
        # Mapping of C preprocessor keys to output dictionary keys
        key_map = {
            "NDIM": "dimension",
            "NXB": "nxb",
            "NYB": "nyb",
            "NZB": "nzb",
            "NGUARD": "nguardcells",
        }
        out_dict = {}
        with open(simulation_h_path, 'r') as fptr:
            for line in fptr:
                line = line.strip()
                match = re.match(pattern, line)
                if match:
                    key, value = match.groups()
                    if key in key_map:
                        # Convert value to an integer
                        try:
                            value = int(value)
                        except ValueError:
                            raise RuntimeError(f"Unable to cast {value} to intger in processing [{line}].")
                        if key_map[key] in out_dict:
                            raise RuntimeError(f"Multiple definitions for {key} are detected")
                        out_dict[key_map[key]] = value

        # write to disk
        if grid_json_path.is_file():
            logger.warning("Overwriting {_file}", _file=grid_json_path)
        with open(grid_json_path, 'w') as fptr:
            json.dump(out_dict, fptr, indent=2)

        # save the path for the grid_json for later use
        self.grid_json_path = grid_json_path


    def _generate_milhoja_codes(self, dest:Path) -> None:
        assert self.tf_data_all is not None

        if not dest.is_dir():
            logger.warning("Making a destination directory: {_dest}", _dest=dest)
            dest.mkdir(exist_ok=True)

        objdir = self.objdir

        for tf_data in self.tf_data_all:
            tf_name = tf_data["name"]

            # construct partial tf spec and dump to objdir
            partial_tf_spec = construct_partial_tf_spec(tf_data)
            partial_tf_json = objdir / f"__{tf_name}.json"
            with open(partial_tf_json, "w") as fptr:
                json.dump(partial_tf_spec, fptr, indent=2)

            # Milhoja
            milhoja_logger = milhoja.BasicLogger(level=1)

            call_graph = tf_data["subroutine_call_graph"]
            group_json_all = tf_data["operation_specs"]
            tfAssembler = milhoja.TaskFunctionAssembler.from_milhoja_json(
                tf_name, call_graph, group_json_all, self.grid_json_path, milhoja_logger
            )

            # generate taskfunction specs
            tf_spec_json = objdir / f"__tf_spec_{tf_name}.json"
            tfAssembler.to_milhoja_json(tf_spec_json, partial_tf_json, overwrite=True)

            # invoke milhoja_pypkg to generate source codes for taskfunction and dataitems
            destination = objdir / dest

            overwrite = True
            indent = 3
            milhoja_path = self.milhoja_path

            tf_spec = milhoja.TaskFunction.from_milhoja_json(tf_spec_json)
            milhoja.generate_data_item(
                tf_spec, destination, overwrite, milhoja_path, indent, milhoja_logger
            )
            milhoja.generate_task_function(
                tf_spec, destination, overwrite, indent, milhoja_logger
            )


    def _generate_TimeAdvance_code(self, dest:Path) -> None:

        flowGraph = self.flowGraph

        flowGraph.parseCode()


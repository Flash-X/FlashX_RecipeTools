import re
from loguru import logger

import cgkit.ctree.srctree as srctree
from cgkit.ctree.srctree import SourceTree

from cgkit.cflow.controller import (
    AbstractControllerGraph,
    AbstractControllerNode,
    AbstractControllerMultiEdge,
    CtrRet,
)

from ..nodes import (
    RootNode,
    SetupNode,
    OrchestrationBeginNode,
    OrchestrationEndNode,
)
from ..utils import TaskfunctionTemplateGenerator
from ..constants import FLASHX_RECIPETOOLS_ROOT

INTERNAL_TEMPLATE_PATH = FLASHX_RECIPETOOLS_ROOT / "TimeStepRecipe" / "_internal_tpl"


def _format_fortran_vardef(line):
    """
    Format a Fortran variable definition line and return a dictionary
    where each dictitem has {variable_name:variable_type} pairs
    """
    assert "::" in line

    variables = dict()

    var_pattern = re.compile(r'(\w+)\s*(\([^)]*\))?')
    parts = line.split("::")
    var_type = parts[0].strip()
    var_names = parts[1].strip()

    # process each variable in the declaration
    matches = var_pattern.findall(var_names)
    for match in matches:
        var_name = match[0]
        dimensions = match[1]
        if dimensions:
            full_type = f"{var_type}, dimension{dimensions}"
        else:
            full_type = var_type
        if var_name in variables.keys():
            raise ValueError(f"Duplicate variable name found: {var_name}")
        # update the variable dictionary
        variables[var_name] = full_type

    return variables


def _determine_dataitem_name(tf_spec):
    """
    A helper function to define variable name for a dataitem consistently
    """
    return f"{tf_spec.data_item}_{tf_spec.name}"

def _format_MHarg_init_codeline(argname, MH_argname, argtype):
    """
    A helper function to generate a code line for
    initialization of MH_* variables
    """
    # handling cpu case    TODO: not sure why this is needed
    if argtype == "milhoja::Real":
        argtype = "real"
    elif argtype == "integer":
        argtype = "int"

    if argtype not in ["real", "int"]:
        msg = f"Unrecognized argument type, {argtype} for {argname}"
        raise RuntimeError(msg)

    MH_type = "MILHOJA_" + argtype.upper()
    return f"{MH_argname} = {argtype}({argname}, kind={MH_type})"

def _format_MHarg_def_codeline(argname, MH_argname, argtype):
    """
    A helper function to generate a code line for
    definition of MH_* variables
    """
    # handling cpu case    TODO: not sure why this is needed
    if argtype == "milhoja::Real":
        argtype = "real"
    elif argtype == "integer":
        argtype = "int"

    if argtype not in ["real", "int"]:
        msg = f"Unrecognized argument type, {argtype} for {argname}"
        raise RuntimeError(msg)

    MH_type = "MILHOJA_" + argtype.upper()
    TYPE_MAPPING = {
        "int": "integer",
        "real": "real",
    }
    return f"{TYPE_MAPPING[argtype]}({MH_type}) :: {MH_argname}"

def _milhoja_check_internal_error():
    """
    A helper function to generate a code line for
    checking Milhoja internal error
    """
    return 'call Orchestration_checkInternalError("TimeAdvance", MH_ierr)'


def _get_null_subroutine_calls(tf_spec):
    """
    A helper function to extract the subroutine calls
    without the device suffixes, e.g., "_cpu" or "_gpu",
    case-insensitively.
    """
    device_pattern = r'_(cpu|gpu)$'
    res = []
    for node in tf_spec.internal_subroutine_graph:
        for sub in node:
            res.append(re.sub(device_pattern, '', sub, flags=re.IGNORECASE))
    return res


class Ctr_InitTAGraph(AbstractControllerGraph):
    def __init__(self):
        super().__init__(controllerType="modify")
        self._devices = []
        self._tfNodes = []
        self._orchBegins = []
        self._orchEnds = []
        self._inConcurrent = False

    def __call__(self, graph, graphAttribute):
        pass

    def getCurrentDevices(self):
        if self.inConcurrent:
            assert isinstance(self._devices[-1], list)
            return self._devices[-1]
        else:
            return self._devices

    def getCurrentTFNodes(self):
        return self._tfNodes

    def pushOrchBegin(self, node):
        assert isinstance(node, int)
        self._orchBegins.append(node)

    def pushOrchEnd(self, node):
        assert isinstance(node, int)
        self._orchEnds.append(node)

    def getCurrentOrchBegin(self):
        return self._orchBegins[-1]

    def getCurrentOrchEnd(self):
        return self._orchEnds[-1]

    @property
    def devices(self):
        return self._devices

    @devices.setter
    def devices(self, value:list):
        self._devices = value

    @property
    def tfNodes(self):
        return self._tfNodes

    @tfNodes.setter
    def tfNodes(self, value:list):
        self._tfNodes = value

    @property
    def inConcurrent(self):
        return self._inConcurrent

    @inConcurrent.setter
    def inConcurrent(self, value:bool):
        self._inConcurrent = value


class Ctr_InitTANode(AbstractControllerNode):
    def __init__(self, ctrInitTAGraph):
        super().__init__(controllerType="modify")
        self._log = logger
        self._ctrInitTAGraph = ctrInitTAGraph

    def __call__(self, graph, node, nodeAttributes):
        nodeObj = nodeAttributes["obj"]

        # if orchestration begins, mark taskfunction nodes
        if isinstance(nodeObj, OrchestrationBeginNode):
            self._ctrInitTAGraph.pushOrchBegin(node)

        # if orchestration ends, mark taskfunction nodes
        if isinstance(nodeObj, OrchestrationEndNode):
            beginNodeID = self._ctrInitTAGraph.getCurrentOrchBegin()
            endNodeID = node
            self._ctrInitTAGraph.pushOrchBegin(endNodeID)

            # mark orchestration pattern
            graph.setNodeAttribute(beginNodeID, "TFNodes", self._ctrInitTAGraph.tfNodes)
            graph.setNodeAttribute(endNodeID, "TFNodes", self._ctrInitTAGraph.tfNodes)
            graph.setNodeAttribute(beginNodeID, "devices", self._ctrInitTAGraph.devices)
            graph.setNodeAttribute(endNodeID, "devices", self._ctrInitTAGraph.devices)

            # reset stashes
            self._ctrInitTAGraph.devices = []
            self._ctrInitTAGraph.tfNodes = []

        if graph.nodeHasSubgraph(node):
            # found taskfunction
            device = nodeAttributes["device"]
            self._ctrInitTAGraph.getCurrentDevices().append(device)
            self._ctrInitTAGraph.getCurrentTFNodes().append(nodeObj)

            sGraph = graph.nodeGetSubgraph(node)
            subGraphAttributes = sGraph.G.graph

            # the actual information for the taskfunction lies in the sub"sub"graph
            # as the cgkit generates two-level subgraph.
            ssGraph = sGraph.nodeGetSubgraph(sGraph.root)
            subsubGraphAttributes = ssGraph.G.graph

            assert isinstance(subGraphAttributes, dict), type(subGraphAttributes)
            assert isinstance(subsubGraphAttributes, dict), type(subsubGraphAttributes)

            # bringing the taskfunction name from sub"sub"graph to subgraph.
            nodeAttributes["tf_name"] = subsubGraphAttributes["tf_name"]
            nodeObj.name = subsubGraphAttributes["tf_name"]

        return CtrRet.SUCCESS


class Ctr_InitTAMultiEdge(AbstractControllerMultiEdge):
    def __init__(self, ctrInitTAGraph):
        super().__init__(controllerType="view")
        self._log = logger
        self._ctrInitTAGraph = ctrInitTAGraph

    def __call__(self, graph, node, nodeAttribute, successors):
        self._log.info("entering multiedge at node = {_node}", _node=node)
        self._ctrInitTAGraph.getCurrentDevices().append(list())
        self._ctrInitTAGraph.inConcurrent = True

    def q(self, graph, node, nodeAttribute, predecessors):
        self._log.info("exiting multiedge at node = {_node}", _node=node)
        # flattening devices
        self._ctrInitTAGraph.devices = [
            '_'.join(item) if isinstance(item, list) else item
            for item in self._ctrInitTAGraph.devices
        ]
        self._ctrInitTAGraph.inConcurrent = False


class Ctr_TAParseGraph(AbstractControllerGraph):
    def __init__(self, tf_spec_all, indentSpace=" " * 3, verbose=False):
        super().__init__(controllerType="view")
        self._log = logger
        self._stree = SourceTree(
            INTERNAL_TEMPLATE_PATH,
            indentSpace,
            verbose=verbose,
            verbosePre="!",
            verbosePost="",
            template_type="mako",
            debug=False,
        )
        self._callReturnStack = list()
        self._variables = dict()
        self._tf_spec_all = tf_spec_all

        self.orchestration_count = 0

    def __call__(self, graph, graphAttribute):
        if not graph.isSubgraph():
            # parse the top-level graph
            self._log.info("Parse top-level graph")
            self._stree.initTree("cg-tpl.TimeAdvance.F90")

            # update variables for the initial template
            self._update_variables(INTERNAL_TEMPLATE_PATH / "cg-tpl.TimeAdvance.F90")

            linkKeyList = srctree.search_links(self._stree.getTree())
            self._stree.pushLink(linkKeyList)
            self._callReturnStack.append(CtrRet.SUCCESS)
        return self._callReturnStack[-1]

    def q(self, graph, graphAttribute):
        assert self._callReturnStack
        if not graph.isSubgraph():
            if CtrRet.SUCCESS == self._callReturnStack.pop():
                self._log.info("Terminate parsing graph at level={_level}", _level=graph.level)
                linkKeyList = self._stree.popLink()
                return CtrRet.SUCCESS
            else:
                return CtrRet.ERROR

    def getSourceTree(self):
        return self._stree

    def getAllTFSpec(self):
        return self._tf_spec_all

    def getVariables(self):
        return self._variables

    def push_variable(self, vardef):
        """
        Push a variable to the dictionary, self._variables.
        The function can take either a Fortran variable definition line
        or a dictionary where each dictitem has {variable_name:variable_type} pairs.
        """
        if isinstance(vardef, str):
            new_variables = _format_fortran_vardef(vardef)
        elif isinstance(vardef, dict):
            var_name, var_type = vardef
            new_variables = _format_fortran_vardef(f"{var_type} :: {var_name}")
        else:
            raise ValueError(f"Unsupported variable definition, {vardef}")

        for var_name, var_type in new_variables.items():
            if var_name in self._variables.keys():
                if var_type == self._variables[var_name]:
                    self._log.warning("{_varname} is already defined. ignoring...", _varname=var_name)
                    return
                else:
                    msg = f"'{var_name}' is already defined as '{self._variables[var_name]}' " + \
                          f"but '{vardef}' is given"
                    raise ValueError(msg)

        # update variable
        self._variables.update(new_variables)

    def _update_variables(self, tpl):
        """
        Parse a Fortran template to extract variable declarations
        and update dictionary, self._variables.

        This function reads a Fortran template line by line,
        handling line continuations, and identifies lines
        containing variable declarations.
        It then constructs and returns a dictionary where
        the keys are variable names and the values are their corresponding types.

        Parameters:
        tpl (str): The path to the Fortran template to be parsed.

        Returns:
        None.

        Example:
        Given the following Fortran code in a file:

            real, dimension(:) :: a, &
                                  b, &
                                  c
            integer :: x, y, z(:,:)

        The function will update self._variables as:
        {
            "a": "real, dimension(:)",
            "b": "real, dimension(:)",
            "c": "real, dimension(:)",
            "x": "integer",
            "y": "integer",
            "z": "integer, dimension(:,:)",
        }
        """
        with open(tpl, 'r') as f:
            lines = f.readlines()

        # combine lines that end with '&'
        combined_lines = []
        current_line = ""

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.endswith('&'):
                current_line += stripped_line[:-1] + ' '
            else:
                current_line += stripped_line
                combined_lines.append(current_line)
                current_line = ""

        # regex to match variable declarations with dimensions
        var_pattern = re.compile(r'(\w+)\s*(\([^)]*\))?')

        for line in combined_lines:
            if "::" in line:
                self._variables.update(_format_fortran_vardef(line))

class Ctr_TAParseNode(AbstractControllerNode):
    def __init__(self, ctrParseGraph, verbose=False):
        super().__init__(controllerType="view")
        self._log = logger
        self._stree = ctrParseGraph.getSourceTree()
        self._tf_spec_all = ctrParseGraph.getAllTFSpec()
        self._ctrParseGraph = ctrParseGraph
        self._beginEnd_callReturnStack = dict()

    def __call__(self, graph, node, nodeAttribute):
        assert "obj" in nodeAttribute, nodeAttribute.keys()
        nodeObj = nodeAttribute["obj"]
        if isinstance(nodeObj, RootNode):
            pass
        elif isinstance(nodeObj, OrchestrationBeginNode):
            return self._call_OrchestrationBeginNode(nodeObj, graph, node, nodeAttribute)
        elif isinstance(nodeObj, OrchestrationEndNode):
            return self._call_OrchestrationEndNode(nodeObj, graph, node, nodeAttribute)
        elif isinstance(nodeObj, SetupNode):
            return self._call_SetupNode(nodeObj, graph, node, nodeAttribute)
        elif graph.nodeHasSubgraph(node):    # taskfunction is constructed in a subgraph
            return self._call_TaskFunctionNode(nodeObj, graph, node, nodeAttribute)
        else:
            self._log.warning("Nothing to parse for node object {_nodeType}", _nodeType=type(nodeObj))
            return CtrRet.VOID

    def _call_OrchestrationBeginNode(self, nodeObj, graph, node, nodeAttribute):
        # increment orchestration count
        self._ctrParseGraph.orchestration_count += 1
        orch_cnt = self._ctrParseGraph.orchestration_count
        self._log.info("Parsing Orchestration invoke {_cnt}", _cnt=orch_cnt)
        # determine orchestration template based on devices
        # TODO: this only works for "pushTile" style
        devices = nodeAttribute["devices"]
        if len(devices) == 1:
            device = devices[0].lower()
            if '_' not in device:
                # found single device pattern
                # device must be cpu or gpu
                if device not in ["cpu", "gpu"]:
                    msg = f"Unrecognized device={device} " + \
                          f"for taskfunction={nodeAttribute['TFNodes'][0].name}"
                    raise RuntimeError(msg)

                tf_name = nodeAttribute["TFNodes"][0].name
                tf_spec = self._tf_spec_all[tf_name]
                self._log.info(
                    "Found single {_device} Action, {_tf_name}",
                    _device=device,
                    _tf_name = tf_name
                )
                # load single device template
                tpl_name = f"cg-tpl.execute_Milhoja_pushTile_{device.capitalize()}Only.json"
                tree = srctree.load(
                    INTERNAL_TEMPLATE_PATH / tpl_name
                )
                tree["_param:orchestration_count"] = str(orch_cnt)
                tree["_param:taskfunction_name"] = str(tf_name)
                tree["_param:dataitem_name"] = _determine_dataitem_name(tf_spec)
                # link tree
                pathInfo = self._stree.link(tree, linkPath=srctree.LINK_PATH_FROM_STACK)
                # update links
                linkKeyList = srctree.search_links(tree)
                self._stree.pushLink(linkKeyList)
            else:
                # found cpu/gpu in parallel pattern
                #    i.e.) devices = ["gpu_cpu"] or ["cpu_gpu"]
                parallel_devices = device.split('_')
                if len(parallel_devices) != 2 or set(parallel_devices) != {"cpu", "gpu"}:
                    msg = f"Unrecognized parallel devices={device}"
                    raise RuntimeError(msg)

                node0_name = nodeAttribute["TFNodes"][0].name
                node1_name = nodeAttribute["TFNodes"][1].name

                if "gpu" in node0_name:
                    tf_name_gpu = node0_name
                    tf_name_cpu = node1_name
                else:
                    tf_name_gpu = node1_name
                    tf_name_cpu = node0_name
                tf_spec_gpu = self._tf_spec_all[tf_name_gpu]
                tf_spec_cpu = self._tf_spec_all[tf_name_cpu]

                # check if it is a cpu/gpu **split** pattern
                call_graph_gpu = _get_null_subroutine_calls(tf_spec_gpu)
                call_graph_cpu = _get_null_subroutine_calls(tf_spec_cpu)
                if call_graph_gpu == call_graph_cpu:
                    # found cpu/gpu split pattern
                    raise NotImplementedError("CPU/GPU split pattern is not implemented yet.")

                # found cpu/gpu pattern
                self._log.info(
                    "Found CPU/GPU Action, {_tf_name_gpu} / {_tf_name_cpu}",
                    _tf_name_gpu = tf_name_gpu,
                    _tf_name_cpu = tf_name_cpu
                )
                tpl_name = "cg-tpl.execute_Milhoja_pushTile_CpuGpu.json"
                tree = srctree.load(
                    INTERNAL_TEMPLATE_PATH / tpl_name
                )
                tree["_param:orchestration_count"] = str(orch_cnt)
                tree["_param:taskfunction_name_cpu"] = str(tf_name_cpu)
                tree["_param:taskfunction_name_gpu"] = str(tf_name_gpu)
                tree["_param:dataitem_name_cpu"] = _determine_dataitem_name(tf_spec_cpu)
                tree["_param:dataitem_name_gpu"] = _determine_dataitem_name(tf_spec_gpu)
                # link tree
                pathInfo = self._stree.link(tree, linkPath=srctree.LINK_PATH_FROM_STACK)
                # update links
                linkKeyList = srctree.search_links(tree)
                self._stree.pushLink(linkKeyList)

        elif len(devices) == 2:
            if devices == ["gpu", "cpu"]:
                # Found extGpuAction
                tf_name_gpu = nodeAttribute["TFNodes"][0].name
                tf_name_cpu = nodeAttribute["TFNodes"][1].name
                tf_spec_gpu = self._tf_spec_all[tf_name_gpu]
                tf_spec_cpu = self._tf_spec_all[tf_name_cpu]
                self._log.info(
                    "Found extended GPU Action, {_tf_name_gpu} then {_tf_name_cpu}",
                    _tf_name_gpu = tf_name_gpu,
                    _tf_name_cpu = tf_name_cpu
                )
                tpl_name = "cg-tpl.execute_Milhoja_pushTile_ExtGpu.json"
                tree = srctree.load(
                    INTERNAL_TEMPLATE_PATH / tpl_name
                )
                tree["_param:orchestration_count"] = str(orch_cnt)
                tree["_param:taskfunction_name_cpu"] = str(tf_name_cpu)
                tree["_param:taskfunction_name_gpu"] = str(tf_name_gpu)
                tree["_param:dataitem_name_cpu"] = _determine_dataitem_name(tf_spec_cpu)
                tree["_param:dataitem_name_gpu"] = _determine_dataitem_name(tf_spec_gpu)
                # link tree
                pathInfo = self._stree.link(tree, linkPath=srctree.LINK_PATH_FROM_STACK)
                # update links
                linkKeyList = srctree.search_links(tree)
                self._stree.pushLink(linkKeyList)
            else:
                raise NotImplementedError("CPU then GPU orchestration (ExtCpu?) is not implemented")
        else:
            raise NotImplementedError("Three devices?")

        return CtrRet.SUCCESS

    def _call_OrchestrationEndNode(self, nodeObj, graph, node, nodeAttribute):
        self._log.info("Ending Orchestration")
        # pop links introduced for taskfunctions
        linkPath = self._stree.popLink()

        return CtrRet.SUCCESS

    def _call_SetupNode(self, nodeObj, graph, node, nodeAttribute):
        self._log.info("Adding a bare template {_name}", _name=nodeObj.name)
        tree = srctree.load(nodeObj.tpl)
        self._stree.link(tree, linkPath=srctree.LINK_PATH_FROM_STACK)

        return CtrRet.SUCCESS



    def _call_TaskFunctionNode(self, nodeObj, graph, node, nodeAttribute):

        tf_name = nodeAttribute["tf_name"]
        tf_spec = self._tf_spec_all[tf_name]
        device = tf_spec.processor

        # TODO: MH_args defs and inits should be in here
        #       to avoid duplicated lines in generated codes
        #       for multi-device cases

        # TODO: self._generate_[CPU/GPU]_taskfunction_tpl functions
        #       have too many duplicated codes
        if device == "gpu":
            tf_tpl = self._generate_GPU_taskfunction_tpl(tf_spec)
        elif device == "cpu":
            tf_tpl = self._generate_CPU_taskfunction_tpl(tf_spec)
        else:
            msg = f"{device} taskfunction generator is not implemented yet"
            raise NotImplementedError(msg)

        # link a taskfunction template to the TimeAdvance
        self._stree.link(tf_tpl.getSourceTree(), linkPath=srctree.LINK_PATH_FROM_STACK)

        return CtrRet.SUCCESS


    def _generate_GPU_taskfunction_tpl(self, tf_spec):
        # init a template for taskfunction
        tf_tpl = TaskfunctionTemplateGenerator()

        code_var_defs = []
        code_var_init = []

        # dealing with external variables
        external_args = tf_spec.constructor_dummy_arguments
        mh_external_vars = []
        for arg in external_args:
            argname, argtype = arg
            arg_spec = tf_spec.argument_specification(argname)

            origin_source = arg_spec["application_specific"]["origin"]
            origin_varname = arg_spec["application_specific"]["varname"]
            argname_short = argname.replace("external_", "")

            mh_var = "MH_" + argname_short
            mh_def_line = _format_MHarg_def_codeline(argname_short, mh_var, argtype)
            mh_init_line = _format_MHarg_init_codeline(origin_varname, mh_var, argtype)

            # update variable in the graph controller
            # it will check the variable duplications
            self._ctrParseGraph.push_variable(mh_def_line)

            mh_external_vars.append(mh_var)
            code_var_defs.append(mh_def_line)
            code_var_init.append(mh_init_line)

        # construct dataitem def
        dataitem_name = _determine_dataitem_name(tf_spec)
        dataitem_def_line = "type(c_ptr) :: " + dataitem_name
        # update dataitem variable
        self._ctrParseGraph.push_variable(dataitem_def_line)
        code_var_defs.append(dataitem_def_line)

        # construct dataitem init
        code_dataitem_init = []
        code_dataitem_init.append(f"{dataitem_name} = c_null_ptr")
        code_dataitem_init.append(f"MH_ierr = {tf_spec.instantiate_packet_C_function}( &")
        for var in mh_external_vars:
            line = ' '*3 + f"{var}, &"
            code_dataitem_init.append(line)
        code_dataitem_init.append(' '*3 + f"{dataitem_name} &")
        code_dataitem_init.append(')')
        # check milhoja internal error
        code_dataitem_init.append(_milhoja_check_internal_error())

        # construct dataitem delete
        code_dataitem_del = []
        code_dataitem_del.append(f"MH_ierr = {tf_spec.delete_packet_C_function}( &")
        code_dataitem_del.append(' '*3 + f"{dataitem_name} &")
        code_dataitem_del.append(')')
        code_dataitem_del.append(_milhoja_check_internal_error())
        code_dataitem_del.append(f"{dataitem_name} = c_null_ptr")

        # construct use interface
        code_use_interface = []
        code_use_interface.append(f"use {tf_spec.fortran_module_name}, ONLY: {tf_spec.cpp2c_layer_name}")
        dataitem_use_line = f"use {tf_spec.data_item_module_name}, ONLY: "
        _use_indent = len(dataitem_use_line)
        code_use_interface.append(dataitem_use_line + f"{tf_spec.instantiate_packet_C_function}, &")
        code_use_interface.append(' '*_use_indent + f"{tf_spec.delete_packet_C_function}")

        # update taskfunction template
        tf_tpl.use_interface = code_use_interface
        tf_tpl.init_dataitem = code_dataitem_init
        tf_tpl.var_definition = code_var_defs
        tf_tpl.var_initialization = code_var_init
        tf_tpl.delete_dataitem = code_dataitem_del

        return tf_tpl


    def _generate_CPU_taskfunction_tpl(self, tf_spec):
        # init a template for taskfunction
        tf_tpl = TaskfunctionTemplateGenerator()

        code_var_defs = []
        code_var_init = []

        # dealing with external variables
        external_args = tf_spec.constructor_dummy_arguments
        mh_external_vars = []
        for arg in external_args:
            argname, argtype = arg
            arg_spec = tf_spec.argument_specification(argname)

            origin_source = arg_spec["application_specific"]["origin"]
            origin_varname = arg_spec["application_specific"]["varname"]
            argname_short = argname.replace("external_", "")

            mh_var = "MH_" + argname_short
            mh_def_line = _format_MHarg_def_codeline(argname_short, mh_var, argtype)
            mh_init_line = _format_MHarg_init_codeline(origin_varname, mh_var, argtype)

            # update variable in the graph controller
            # it will check the variable duplications
            self._ctrParseGraph.push_variable(mh_def_line)

            mh_external_vars.append(mh_var)
            code_var_defs.append(mh_def_line)
            code_var_init.append(mh_init_line)

        # construct dataitem def
        dataitem_name = _determine_dataitem_name(tf_spec)
        dataitem_def_line = "type(c_ptr) :: " + dataitem_name
        # update dataitem variable
        self._ctrParseGraph.push_variable(dataitem_def_line)
        code_var_defs.append(dataitem_def_line)

        # construct dataitem init
        code_dataitem_init = []
        code_dataitem_init.append(f"MH_ierr = {tf_spec.acquire_scratch_C_function}()")
        code_dataitem_init.append(_milhoja_check_internal_error())
        code_dataitem_init.append("")

        code_dataitem_init.append(f"{dataitem_name} = c_null_ptr")
        code_dataitem_init.append(f"MH_ierr = {tf_spec.instantiate_packet_C_function}( &")
        for var in mh_external_vars:
            line = ' '*3 + f"{var}, &"
            code_dataitem_init.append(line)
        code_dataitem_init.append(' '*3 + f"{dataitem_name} &")
        code_dataitem_init.append(')')
        # check milhoja internal error
        code_dataitem_init.append(_milhoja_check_internal_error())

        # construct dataitem delete
        code_dataitem_del = []
        code_dataitem_del.append(f"MH_ierr = {tf_spec.delete_packet_C_function}( &")
        code_dataitem_del.append(' '*3 + f"{dataitem_name} &")
        code_dataitem_del.append(')')
        code_dataitem_del.append(_milhoja_check_internal_error())
        code_dataitem_del.append(f"{dataitem_name} = c_null_ptr")
        code_dataitem_del.append("")
        code_dataitem_del.append(f"MH_ierr = {tf_spec.release_scratch_C_function}()")
        code_dataitem_del.append(_milhoja_check_internal_error())

        # construct use interface
        code_use_interface = []
        code_use_interface.append(f"use {tf_spec.fortran_module_name}, ONLY: {tf_spec.cpp2c_layer_name}")
        dataitem_use_line = f"use {tf_spec.data_item_module_name}, ONLY: "
        _use_indent = len(dataitem_use_line)
        code_use_interface.append(dataitem_use_line + f"{tf_spec.instantiate_packet_C_function}, &")
        code_use_interface.append(' '*_use_indent + f"{tf_spec.delete_packet_C_function}, &")
        code_use_interface.append(' '*_use_indent + f"{tf_spec.acquire_scratch_C_function}, &")
        code_use_interface.append(' '*_use_indent + f"{tf_spec.release_scratch_C_function}")

        # update taskfunction template
        tf_tpl.use_interface = code_use_interface
        tf_tpl.init_dataitem = code_dataitem_init
        tf_tpl.var_definition = code_var_defs
        tf_tpl.var_initialization = code_var_init
        tf_tpl.delete_dataitem = code_dataitem_del

        return tf_tpl


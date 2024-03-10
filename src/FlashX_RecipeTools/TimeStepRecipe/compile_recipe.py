from .TimeStepRecipe import TimeStepRecipe
from ._controller import (
    Ctr_InitNodeFromOpspec,
    Ctr_SetupEdge,
    Ctr_MarkEdgeAsKeep,
    Ctr_InitSubgraph,
    Ctr_ParseTFGraph,
    Ctr_ParseTFNode,
    Ctr_ParseTFMultiEdge,
)
from .construct_partial_tf_spec import construct_partial_tf_spec


SUPPORTED = {
    "processor": ["gpu"],
    "computation_offloading": ["OpenACC"],
    "data_type": ["DataPacket"],
}


def determine_output_files(tfData_all:list) -> set:
    """
    Determines file names to be generated by Milhoja_pypkg,
    and check if they are valid
    """
    output_files = set()
    # assuming taskfunction language is Fortran
    for tfData in tfData_all:
        # get partial task function spec
        partial_tf_spec = construct_partial_tf_spec(tfData)
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

        # determine files too be generated
        if offloading == "OpenACC":
            files_to_be_generated = [
                task_function["cpp_source"],
                task_function["c2f_source"],
                task_function["fortran_source"],
            ]
            for filename in files_to_be_generated:
                # filename must be unique
                if filename in output_files:
                    raise ValueError(f"Duplicate filename detected: {filename}")
                output_files.add(filename)

        if data_type == "DataPacket":
            files_to_be_generated = [
                data_item["header"],
                data_item["module"],
                data_item["source"],
            ]
            for filename in files_to_be_generated:
                # filename must be unique
                if filename in output_files:
                    raise ValueError(f"Duplicate filename detected: {filename}")
                output_files.add(filename)

    return output_files


def compile_recipe(recipe:TimeStepRecipe) -> list:
    # gather argument list of each nodes
    recipe.traverse(controllerNode=Ctr_InitNodeFromOpspec())

    # transform into hierarchical graph
    recipe.traverse(controllerEdge=Ctr_SetupEdge())
    h = recipe.extractHierarchicalGraph(
        controllerMarkEdge=Ctr_MarkEdgeAsKeep(),
        controllerInitSubgraph=Ctr_InitSubgraph()
    )

    # generate intermediate TF data
    ctrParseTFGraph = Ctr_ParseTFGraph()
    ctrParseTFNode = Ctr_ParseTFNode(ctrParseTFGraph)
    ctrParseTFMultiedge = Ctr_ParseTFMultiEdge(ctrParseTFGraph)
    h.traverseHierarchy(
        controllerGraph=ctrParseTFGraph,
        controllerNode=ctrParseTFNode,
        controllerMultiEdge=ctrParseTFMultiedge
    )

    tfData_all = list(ctrParseTFGraph.getAllTFData())
    output_files = determine_output_files(tfData_all)
    # assign output file names to recipe object
    recipe.set_output_fnames(output_files)

    return tfData_all


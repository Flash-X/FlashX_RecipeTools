#TODO: structure tfdata as an object

from milhoja.milhoja_pypkg_opts import opts

def construct_partial_tf_spec(tf_data) -> dict:
    """
    Construct partial TF spec from given TF (meta)data
    """
    tf_name = tf_data["name"]
    processor = tf_data["processor"]

    # TODO: this may be in tfData
    data_item = "TileWrapper"
    offloading = ""
    if processor.lower() == "gpu":
        data_item = "DataPacket"
        # Expected: "OpenACC" or "OpenMP"; maybe None?
        offloading = opts['computation_offloading']

    partial_tf_spec = {
        "task_function": {
            "language": "Fortran",
            "processor": processor,
            "computation_offloading": offloading,
            "variable_index_base": 1,
            "cpp_header": f"{tf_name}.h",
            "cpp_source": f"{tf_name}.cxx",
            "c2f_source": f"{tf_name}_C2F.F90",
            "fortran_source": f"{tf_name}_mod.F90",
        },
        "data_item": {
            "type": data_item,
            "byte_alignment": 1,
            "header": f"{data_item}_{tf_name}.h",
            "module": f"{data_item}_{tf_name}_mod.F90",
            "source": f"{data_item}_{tf_name}.cxx",
        },
    }

    return partial_tf_spec


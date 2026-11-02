#TODO: structure tfdata as an object

def construct_partial_tf_spec(tf_data) -> dict:
    """
    Consruct partial TF spec from given TF (meta)data
    """
    tf_name = tf_data["name"]
    processor = tf_data["processor"]

    # Callers may now request a DataPacket independently of the processor.
    # This is needed by the Milhoja HOSTMEM runtime. Existing callers retain
    # the CPU/TileWrapper and GPU/DataPacket defaults.
    data_item = tf_data.get("data_item")
    if data_item is None:
        data_item = "DataPacket" if processor.lower() == "gpu" else "TileWrapper"
    if data_item.lower() not in {"tilewrapper", "datapacket"}:
        raise ValueError(f"Unsupported data item {data_item}")

    offloading = tf_data.get("computation_offloading")
    if offloading is None:
        offloading = "OpenACC" if processor.lower() == "gpu" else ""

    default_alignment = 16 if data_item.lower() == "datapacket" else 1
    byte_alignment = tf_data.get("byte_alignment", default_alignment)

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
            "byte_alignment": byte_alignment,
            "header": f"{data_item}_{tf_name}.h",
            "module": f"{data_item}_{tf_name}_mod.F90",
            "source": f"{data_item}_{tf_name}.cxx",
        },
    }

    if "data_layout" in tf_data:
        partial_tf_spec["data_item"]["data_layout"] = tf_data["data_layout"]

    return partial_tf_spec


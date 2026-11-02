import pytest

from FlashX_RecipeTools.TimeStepRecipe.construct_partial_tf_spec import (
    construct_partial_tf_spec,
)


def test_cpu_datapacket_hostmem_specification():
    result = construct_partial_tf_spec({
        "name": "host_task",
        "processor": "CPU",
        "data_item": "DataPacket",
        "computation_offloading": "",
    })

    assert result["task_function"]["processor"] == "CPU"
    assert result["task_function"]["computation_offloading"] == ""
    assert result["data_item"]["type"] == "DataPacket"
    assert result["data_item"]["byte_alignment"] == 16


def test_existing_defaults_are_preserved():
    cpu = construct_partial_tf_spec({"name": "cpu_task", "processor": "CPU"})
    gpu = construct_partial_tf_spec({"name": "gpu_task", "processor": "GPU"})

    assert cpu["data_item"]["type"] == "TileWrapper"
    assert cpu["task_function"]["computation_offloading"] == ""
    assert gpu["data_item"]["type"] == "DataPacket"
    assert gpu["task_function"]["computation_offloading"] == "OpenACC"


def test_unknown_data_item_is_rejected():
    with pytest.raises(ValueError, match="Unsupported data item"):
        construct_partial_tf_spec({
            "name": "bad_task",
            "processor": "CPU",
            "data_item": "UnknownItem",
        })


def test_data_layout_is_propagated_when_requested():
    result = construct_partial_tf_spec({
        "name": "layout_task",
        "processor": "CPU",
        "data_item": "DataPacket",
        "data_layout": "variable-first",
    })

    assert result["data_item"]["data_layout"] == "variable-first"

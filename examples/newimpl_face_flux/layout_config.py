"""Canonical layout names and source bindings for the face-flux example."""

VARIABLE_LAST = "variable-last"
VARIABLE_FIRST = "variable-first"
LAYOUT_CHOICES = (VARIABLE_LAST, VARIABLE_FIRST)

LAYOUT_BINDINGS = {
    VARIABLE_LAST: "milhoja_host_layout.ini",
    VARIABLE_FIRST: "milhoja_host_layout_variable_first.ini",
}

DEVICE_LAYOUT_BINDINGS = {
    VARIABLE_LAST: "milhoja_device_layout.ini",
    VARIABLE_FIRST: "milhoja_device_layout_variable_first.ini",
}

ADAPTER_SOURCES = {
    VARIABLE_LAST: "newimpl_face_flux_adapter_mod.F90",
    VARIABLE_FIRST: "newimpl_face_flux_adapter_variable_first_mod.F90",
}


def layout_binding(here, layout):
    return here / LAYOUT_BINDINGS[layout]


def device_layout_binding(here, layout):
    return here / DEVICE_LAYOUT_BINDINGS[layout]


def adapter_source(here, layout):
    return here / ADAPTER_SOURCES[layout]

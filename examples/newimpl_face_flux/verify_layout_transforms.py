#!/usr/bin/env python3
"""Numerically verify the Step 4 packet-layout transforms on the host."""

from layout_config import LAYOUT_CHOICES, VARIABLE_FIRST, VARIABLE_LAST


def _offset(layout, cell, variable, ncells, nvars):
    if layout == VARIABLE_LAST:
        return cell + ncells * variable
    if layout == VARIABLE_FIRST:
        return variable + nvars * cell
    raise ValueError("Unsupported layout {!r}".format(layout))


def _source_offset(tile, cell, variable, ncells, nvars):
    """Offset in the existing variable-last TileFlashxr storage."""
    return tile * ncells * nvars + cell + ncells * variable


def _packet_offset(layout, tile, cell, variable, ncells, nvars):
    return tile * ncells * nvars + _offset(
        layout, cell, variable, ncells, nvars
    )


def _value(tile, cell, variable):
    return 1000000 * tile + 1000 * variable + cell + 1


def _pack(source, layout, ntiles, ncells, nvars, first, last):
    packet = [-1] * (ntiles * ncells * nvars)
    for tile in range(ntiles):
        for cell in range(ncells):
            for variable in range(first, last + 1):
                packet[_packet_offset(
                    layout, tile, cell, variable, ncells, nvars
                )] = source[_source_offset(
                    tile, cell, variable, ncells, nvars
                )]
    return packet


def _unpack(packet, destination, layout, ntiles, ncells, nvars, first, last):
    for tile in range(ntiles):
        for cell in range(ncells):
            for variable in range(first, last + 1):
                destination[_source_offset(
                    tile, cell, variable, ncells, nvars
                )] = packet[_packet_offset(
                    layout, tile, cell, variable, ncells, nvars
                )]


def _verify_state_pack(layout):
    ntiles, ncells, nvars = 2, 22 * 22, 8
    source = [
        _value(tile, cell, variable)
        for tile in range(ntiles)
        for variable in range(nvars)
        for cell in range(ncells)
    ]
    packet = _pack(source, layout, ntiles, ncells, nvars, 0, nvars - 1)
    for tile in range(ntiles):
        for variable in range(nvars):
            for cell in range(ncells):
                assert packet[_packet_offset(
                    layout, tile, cell, variable, ncells, nvars
                )] == _value(tile, cell, variable)

    # A nonzero component mask checks that packet indices retain the absolute
    # component number used by Milhoja's generated C-to-Fortran shape.
    packet = _pack(source, layout, ntiles, ncells, nvars, 2, 5)
    for tile in range(ntiles):
        for variable in range(nvars):
            for cell in range(ncells):
                actual = packet[_packet_offset(
                    layout, tile, cell, variable, ncells, nvars
                )]
                expected = _value(tile, cell, variable) if 2 <= variable <= 5 else -1
                assert actual == expected


def _verify_flux_unpack(layout, nx, ny):
    ntiles, ncells, nvars = 2, nx * ny, 5
    packet = [-1] * (ntiles * ncells * nvars)
    for tile in range(ntiles):
        for variable in range(nvars):
            for cell in range(ncells):
                packet[_packet_offset(
                    layout, tile, cell, variable, ncells, nvars
                )] = _value(tile, cell, variable)

    untouched = -99
    destination = [untouched] * len(packet)
    _unpack(
        packet, destination, layout, ntiles, ncells, nvars, 0, nvars - 1
    )
    expected = [
        _value(tile, cell, variable)
        for tile in range(ntiles)
        for variable in range(nvars)
        for cell in range(ncells)
    ]
    assert destination == expected


def _verify_scratch_offsets(layout, ncells, nvars):
    offsets = {
        _offset(layout, cell, variable, ncells, nvars)
        for variable in range(nvars)
        for cell in range(ncells)
    }
    assert offsets == set(range(ncells * nvars))


def verify_layout_transforms():
    for layout in LAYOUT_CHOICES:
        _verify_state_pack(layout)
        _verify_flux_unpack(layout, 17, 16)
        _verify_flux_unpack(layout, 16, 17)
        _verify_scratch_offsets(layout, 18 * 18, 1)
        _verify_scratch_offsets(layout, 18 * 18, 7)


def main():
    verify_layout_transforms()
    print("NewImpl HOSTMEM dual-layout transform verification passed")


if __name__ == "__main__":
    main()

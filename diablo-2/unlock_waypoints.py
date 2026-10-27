#!/usr/bin/env python3
"""Unlock every waypoint in all three difficulties of a classic Diablo II .d2s save."""

import argparse
import struct
from pathlib import Path

SAVE_MAGIC = 0xAA55AA55
CLASSIC_VERSION = 0x60
WAYPOINT_MARKER = b"WS"
WAYPOINT_OFFSETS = (643, 667, 691)
ALL_WAYPOINTS = ((1 << 39) - 1).to_bytes(5, "little")


def calculate_checksum(data: bytearray) -> int:
    """Calculate the classic .d2s checksum, treating the checksum field as zero."""
    checksum = 0
    for offset, byte in enumerate(data):
        if 12 <= offset < 16:
            byte = 0
        checksum = ((checksum << 1) | (checksum >> 31)) & 0xFFFFFFFF
        checksum = (checksum + byte) & 0xFFFFFFFF
    return checksum


def unlock_waypoints(source: Path, destination: Path) -> None:
    data = bytearray(source.read_bytes())
    if len(data) < 16 or struct.unpack_from("<I", data, 0)[0] != SAVE_MAGIC:
        raise ValueError(f"{source} is not a valid classic Diablo II save.")
    if struct.unpack_from("<I", data, 4)[0] != CLASSIC_VERSION:
        raise ValueError("Unsupported save version; expected classic version 0x60.")
    if struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError("Save header size does not match the actual file size.")
    if calculate_checksum(data) != struct.unpack_from("<I", data, 12)[0]:
        raise ValueError("Save checksum is invalid; refusing to modify the file.")

    marker = data.find(WAYPOINT_MARKER, 16)
    if marker < 0:
        raise ValueError("Could not find the waypoint section in this save.")

    # Legacy saves store three 24-byte difficulty records after the 8-byte section header.
    offsets = tuple(marker + 8 + difficulty * 24 + 2 for difficulty in range(3))
    if offsets[-1] + len(ALL_WAYPOINTS) > len(data):
        raise ValueError("Waypoint section is incomplete; refusing to modify the file.")

    for offset in offsets:
        data[offset : offset + len(ALL_WAYPOINTS)] = ALL_WAYPOINTS

    struct.pack_into("<I", data, 12, 0)
    struct.pack_into("<I", data, 12, calculate_checksum(data))

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)

    written = destination.read_bytes()
    if calculate_checksum(bytearray(written)) != struct.unpack_from("<I", written, 12)[0]:
        raise OSError("Output save failed checksum verification.")
    for offset in offsets:
        if written[offset : offset + len(ALL_WAYPOINTS)] != ALL_WAYPOINTS:
            raise OSError("Output save failed waypoint verification.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unlock all waypoints in a classic Diablo II .d2s save."
    )
    parser.add_argument("input", type=Path, help="Path to the original .d2s save")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Output .d2s path (default: <name>_waypoints_unlocked.d2s)",
    )
    args = parser.parse_args()

    source = args.input
    destination = args.output or source.with_name(
        f"{source.stem}_waypoints_unlocked{source.suffix}"
    )
    if source.resolve() == destination.resolve():
        parser.error("Input and output paths must be different to preserve the original.")

    unlock_waypoints(source, destination)
    print(f"Unlocked all waypoints in Normal, Nightmare, and Hell.")
    print(f"Output: {destination}")


if __name__ == "__main__":
    main()

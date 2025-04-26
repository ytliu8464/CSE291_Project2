#!/usr/bin/env python3
"""
netlist2graph.py

Parse the netlist (in .def file) to two text files in plain‑ASCII format:

1. **hypergraph.txt**
   ```
   Number of vertices: <total>
     Number of macros+std_cells: <total_cell_number>
     Number of IOs: <total_io_number>
   hyperedges: driver_id load_id1 load_id2 ...
   <v0 v1 v2 ...>
   <v3 v4 ...>
   ...
   ```
   Each following line represents one hyper‑edge (a net) with vertex ID

2. **vertex_info.txt**
   ```
   vertex_id, vertex_name, is_fixed, x, y
   0, U0, 0, 0, 0
   1, U1, 1, 1234, 4567
   2, PAD0, 1, 7890, 1350
   ...
   ```
   *is_fixed* is `1` when the vertex has fixed coordinates, 0 otherwise.

"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger(__name__)


@dataclass
class GraphData:
    """Container for all parsed graph information."""

    total_cell_number: int
    total_io_number: int
    fixed_node_num: int
    fixed_id: List[int]
    fixed_pos: List[List[int]]
    movable_id: List[int]
    io_id: List[int]
    io_pos: List[List[int]]
    net_cell_index: List[List[int]]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_def_file(def_path: Path) -> tuple[GraphData, Dict[str, int]]:
    """Parse the DEF file and return graph data plus a name‑to‑index map."""

    info = def_path.read_text(encoding="utf-8", errors="ignore")

    # --- Nets section ---------------------------------------------------- #
    nets_start = re.search(r"\bnets\s+\d+\s*;", info, flags=re.IGNORECASE)
    nets_end = re.search(r"\bend\s+nets\s+", info, flags=re.IGNORECASE)
    if not nets_start or not nets_end:
        raise ValueError("NETS section not found in DEF file.")
    net_info = info[nets_start.start(): nets_end.start()]

    # --- Components section --------------------------------------------- #
    total_cell_number = int(
        re.search(r"COMPONENTS\s+(\d+)\s*;", info, flags=re.IGNORECASE).group(1)
    )

    comp_section = info[info.find("COMPONENTS"): info.find("END COMPONENTS")]
    comp_entries = [e.strip() for e in comp_section.split(";") if e.strip()][1:]  # skip header line

    movable_id: List[int] = []
    fixed_id: List[int] = []
    fixed_pos: List[List[int]] = []
    cell_name_to_index: Dict[str, int] = {}

    movable_counter = 0
    for orig_idx, entry in enumerate(comp_entries):
        cell_name = re.split(r"\s+", re.search(r"-\s+(.*)", entry).group(1))[0]
        cell_name_to_index[cell_name] = orig_idx
        tokens = entry.split()

        if "FIXED" in tokens:
            fixed_id.append(orig_idx)
            pos_idx = tokens.index("FIXED") + 2
            fixed_pos.append([int(tokens[pos_idx]), int(tokens[pos_idx + 1])])
        else:
            movable_id.append(orig_idx)
            movable_counter += 1

    # --- Pins section ---------------------------------------------------- #
    total_io_number = int(re.search(r"pins\s+(\d+)", info, flags=re.IGNORECASE).group(1))
    pins_section = info[info.find("PINS"): info.find("END PINS")]
    pin_entries = [e.strip() for e in pins_section.split(";") if e.strip()][1:]

    io_id: List[int] = []
    io_pos: List[List[int]] = []

    for offset, pin_entry in enumerate(pin_entries):
        pin_name = pin_entry.split()[1]
        idx = offset + total_cell_number
        cell_name_to_index[pin_name] = idx
        io_id.append(idx)
        pos_line = pin_entry.split("\n")[-1]
        io_pos.append([int(pos_line.split()[3]), int(pos_line.split()[4])])

    # --- Nets connectivity ---------------------------------------------- #
    subnet_regex = re.compile(r"-\s+(.*?)\s")
    connect_regex = re.compile(r"\(\s+(.*?)\s+(.*?)\s+\)")
    net_cell_index: List[List[int]] = []

    for net_entry in [e for e in net_info.split(";") if e.strip()]:
        net_match = subnet_regex.search(net_entry)
        if not net_match or net_match.group(1) == "clk_i":
            continue  # skip clock net or malformed line
        cells: List[int] = []
        for token_a, token_b in connect_regex.findall(net_entry):
            target = token_b if token_a == "PIN" else token_a
            cells.append(cell_name_to_index[target])
        net_cell_index.append(cells)

    graph_data = GraphData(
        total_cell_number=total_cell_number,
        total_io_number=total_io_number,
        fixed_node_num=len(fixed_id),
        fixed_id=fixed_id,
        fixed_pos=fixed_pos,
        movable_id=movable_id,
        io_id=io_id,
        io_pos=io_pos,
        net_cell_index=net_cell_index,
    )

    LOGGER.info(
        "Parsed DEF: %s components, %s ios, %s nets",
        total_cell_number,
        total_io_number,
        len(net_cell_index),
    )
    return graph_data, cell_name_to_index


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_hypergraph(graph_data: GraphData, path: Path) -> None:
    """Write the hyper‑graph summary to *hypergraph.txt*."""

    total_vertices = graph_data.total_cell_number + graph_data.total_io_number
    with path.open("w", encoding="ascii") as fh:
        fh.write(f"Number of vertices: {total_vertices}\n")
        fh.write(f"  Number of macros + std_cells: {graph_data.total_cell_number}\n")
        fh.write(f"  Number of IOs: {graph_data.total_io_number}\n")
        fh.write("hyperedges: driver_id load_id1 load_id2 ...\n")
        for edge in graph_data.net_cell_index:
            fh.write(" ".join(map(str, edge)) + "\n")

    LOGGER.info("Wrote hypergraph to %s", path)


def write_vertex_info(
        graph_data: GraphData, name_map: Dict[str, int], path: Path
) -> None:
    """Write detailed vertex information to *vertex_info.txt*."""

    id_to_name = {v: k for k, v in name_map.items()}
    fixed_set = set(graph_data.fixed_id)
    io_set = set(graph_data.io_id)

    with path.open("w", encoding="ascii") as fh:
        # fh.write("vertex_id, type, vertex_name, is_fixed, x, y\n")
        fh.write("vertex_id, vertex_name, is_fixed, x, y\n")
        total_vertices = graph_data.total_cell_number + graph_data.total_io_number
        for vid in range(total_vertices):
            vname = id_to_name.get(vid, f"UNRESOLVED_{vid}")

            if vid in io_set:
                # vtype = "IO"
                is_fixed = 1
                idx = graph_data.io_id.index(vid)
                x, y = graph_data.io_pos[idx]
            elif vid in fixed_set:
                # vtype = "macro"
                is_fixed = 1
                idx = graph_data.fixed_id.index(vid)
                x, y = graph_data.fixed_pos[idx]
            else:
                # vtype = "std_cell"
                is_fixed = 0
                x = y = 0

            # fh.write(f"{vid}, {vtype}, {vname}, {is_fixed}, {x}, {y}\n")
            fh.write(f"{vid}, {vname}, {is_fixed}, {x}, {y}\n")

    LOGGER.info("Wrote vertex info to %s", path)


# ---------------------------------------------------------------------------
# CLI entry‑point
# ---------------------------------------------------------------------------

def main() -> None:
    ### example
    def_file = Path("3_2_place_iop.def")  # [.def file]
    out_dir = Path("./")  # save path

    graph_data, name_map = parse_def_file(def_file)

    write_hypergraph(graph_data, out_dir / "hypergraph.txt")
    write_vertex_info(graph_data, name_map, out_dir / "vertex_info.txt")


if __name__ == "__main__":
    main()

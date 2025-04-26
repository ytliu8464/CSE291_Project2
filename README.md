# CSE291_Project#2

This repo contains two scripts using Python3 

| Script                 | Purpose                                                                                                                                                             |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`netlist2graph.py`** | Parse the netlist to a hypergraph:<br>  • `hypergraph.txt` – a compact hypergraph of the netlist<br>  • `vertex_info.txt` – [vertex_ID, vertex_name, is_fixed, x, y] |
| **`loc2def.py`**       | Take a list of predicted **movable cell** coordinates and patch them back into the .def file, replacing every `UNPLACED` component with `PLACED ( x y ) N`.      |

---

## 1. `netlist2graph.py`

* Scans the `COMPONENTS`, `PINS`, and `NETS` sections of the input DEF.
* Assigns every **component** and **IO pin** a contiguous vertex ID.
* Saves:
  * `hypergraph.txt`

    ```
    Number of vertices: <total>
      Number of macros + std_cells: <total_cell_number>
      Number of IOs: <total_io_number>
    hyperedges: driver_id load_id1 load_id2 ...
    0 17 25
    1 4 9 11
    ...
    ```

  * `vertex_info.txt`

    ```
    vertex_id, vertex_name, is_fixed, x, y
    0, U0, 0, 0, 0
    1, U1, 1, 2280, 2800
    2, PAD0, 1, 45500, 0
    ...
    ```
## 2. `loc2def.py`

* Reads a CSV / Numpy text file containing one (x, y) pair for every
movable cells (order must match the order in the DEF’s COMPONENTS
section).
* Re-writes the DEF file, replacing each UNPLACED with the predicted locations.

  * The original `3_2_place_iop.def`

    ```
    - _2975_ INV_X1 + UNPLACED ;
    - _2976_ BUF_X1 + UNPLACED ;
    - _2977_ INV_X1 + UNPLACED ;
    - _2978_ BUF_X1 + UNPLACED ;
    ```
    
  * The modified `3_2_place_iop.def`

    ```
    - _2975_ INV_X1 + PLACED ( 1192114 2709123 ) N ;
    - _2976_ BUF_X1 + PLACED ( 1378472 2889836 ) N ;
    - _2977_ INV_X1 + PLACED ( 1376774 2889722 ) N ;
    - _2978_ BUF_X1 + PLACED ( 1375933 2889801 ) N ;
    ```


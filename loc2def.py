from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence
import numpy as np

logger = logging.getLogger(__name__)


def save_locations_to_def(
        def_path: Path,
        positions: Sequence[Sequence[float]],
        out_path: Path,
) -> None:
    """
    Inject predicted locations for movable cells into a DEF file.

    Parameters
    ----------
    def_path : Path
        Path to the source `.def` file (i.e., the original 3_2_place_iop.def).
    positions : Sequence[Sequence[float]]
        Iterable shaped (n, 2) containing (x, y) coordinates for *n* movable cells.
        [Note] Locations include only movable cells, and their order must matches the order of components listed in the COMPONENTS section.
    out_path : Path
        Destination path for the new `.def` file. The function appends the
        `.def` suffix automatically if it is missing.
        [Note] Save it as 3_2_place_iop.def and replace the original 3_2_place_iop.def

    """

    if out_path.suffix.lower() != ".def":
        out_path = out_path.with_suffix(".def")

    pos_iter: Iterable[Sequence[float]] = iter(positions)

    with def_path.open("r") as src, out_path.open("w") as dst:
        for line in src:
            if "UNPLACED" in line:
                try:
                    x, y = next(pos_iter)
                except StopIteration as exc:
                    raise ValueError(
                        "Fewer positions than UNPLACED components in DEF file."
                    ) from exc

                line = line.replace(
                    "UNPLACED", f"PLACED ( {int(x)} {int(y)} ) N", 1
                )
            dst.write(line)

    # Check if extra positions were supplied
    try:
        next(pos_iter)
        logger.warning(
            "More positions provided than UNPLACED components—extra values ignored."
        )
    except StopIteration:
        pass


if __name__ == '__main__':
    ### example
    locations = np.loadtxt("xxx.csv", delimiter=',')  # shape (n, 2)
    save_locations_to_def(
        Path("original_3_2_place_iop.def"),
        locations,
        Path("3_2_place_iop.def"),
    )

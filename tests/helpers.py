"""Shared test helpers."""

import json

SQUARE_001 = [[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]
CSV_HEADER = "plot_id,plot_area_m2,tree_id,dbh_cm,height_m,wood_density\n"
ONE_TREE_CSV = CSV_HEADER + "P1,400,T1,20,15,0.6\n"


def polygon_text(*rings: list[list[float]]) -> str:
    return json.dumps({"type": "Polygon", "coordinates": list(rings)})

"""Input and result models of a calculation run. All models are frozen."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from carbon_preaudit.calc.params import DEFAULT_BUFFER_PCT, MAX_WOOD_DENSITY_G_CM3

type Float = Annotated[float, Field(allow_inf_nan=False)]
type Position = tuple[Float, Float]
type Ring = tuple[Position, ...]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Tree(_Frozen):
    """A single measured tree."""

    plot_id: str = Field(min_length=1)
    tree_id: str = Field(min_length=1)
    dbh_cm: float = Field(gt=0, allow_inf_nan=False)
    height_m: float = Field(gt=0, allow_inf_nan=False)
    wood_density_g_cm3: float | None = Field(
        default=None, gt=0, le=MAX_WOOD_DENSITY_G_CM3, allow_inf_nan=False
    )


class Plot(_Frozen):
    """A sample plot with its trees."""

    plot_id: str = Field(min_length=1)
    plot_area_m2: float = Field(gt=0, allow_inf_nan=False)
    trees: tuple[Tree, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _trees_consistent(self) -> Self:
        ids = [t.tree_id for t in self.trees]
        if len(set(ids)) != len(ids):
            raise ValueError(f"plot {self.plot_id}: tree_id must be unique within a plot")
        for t in self.trees:
            if t.plot_id != self.plot_id:
                raise ValueError(
                    f"tree {t.tree_id} has plot_id {t.plot_id!r}, expected {self.plot_id!r}"
                )
        return self


class GeoJSONPolygon(_Frozen):
    """A GeoJSON Polygon (WGS84, lon/lat): outer ring first, then holes."""

    type: Literal["Polygon"]
    coordinates: tuple[Ring, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _rings_closed(self) -> Self:
        for ring in self.coordinates:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("polygon rings must be closed with at least 4 positions")
            for lon, lat in ring:
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError(f"position [{lon}, {lat}] is outside lon/lat range")
        return self


class ProjectInputs(_Frozen):
    """Everything a calculation run depends on."""

    polygon: GeoJSONPolygon
    plots: tuple[Plot, ...] = Field(min_length=1)
    buffer_pct: float = Field(default=DEFAULT_BUFFER_PCT, ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def _plot_ids_unique(self) -> Self:
        ids = [p.plot_id for p in self.plots]
        if len(set(ids)) != len(ids):
            raise ValueError("plot_id must be unique")
        return self


class PlotResult(_Frozen):
    """Result for one plot."""

    plot_id: str
    plot_area_ha: float = Field(allow_inf_nan=False)
    agb_kg: float = Field(allow_inf_nan=False)
    tco2e: float = Field(allow_inf_nan=False)


class CalculationRun(_Frozen):
    """Result of a calculation run, identified by its hash."""

    run_hash: str
    params_version: str
    calc_version: str
    project_area_ha: float = Field(allow_inf_nan=False)
    plot_count: int
    tree_count: int
    trees_with_default_density: int
    tco2e_per_ha: float = Field(allow_inf_nan=False)
    tco2e_gross: float = Field(allow_inf_nan=False)
    buffer_pct: float = Field(allow_inf_nan=False)
    tco2e_buffer: float = Field(allow_inf_nan=False)
    tco2e_net: float = Field(allow_inf_nan=False)
    plots: tuple[PlotResult, ...]

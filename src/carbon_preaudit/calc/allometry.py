"""Allometric biomass (Chave et al. 2014) and conversion to CO2e."""

from carbon_preaudit.calc.params import CARBON_FRACTION, CHAVE_A, CHAVE_B, CO2_PER_C


def agb_kg(wood_density_g_cm3: float, dbh_cm: float, height_m: float) -> float:
    """Return above-ground biomass of one tree in kg."""
    return CHAVE_A * (wood_density_g_cm3 * dbh_cm**2 * height_m) ** CHAVE_B


def tco2e_from_agb_kg(agb: float) -> float:
    """Convert biomass in kg to tonnes CO2e."""
    return agb / 1000 * CARBON_FRACTION * CO2_PER_C

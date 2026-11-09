"""Independent reference tests for satellite vegetation and moisture indices.

Follows strict test integrity:
- Uses verified analytical hand-calculations.
- Tests zero-denominators, NaN inputs, negative reflectance, and scaling.
"""

import numpy as np
import pytest

from backend.app.intelligence.geospatial.indices import calculate_ndvi, calculate_ndmi


def test_ndvi_hand_calculated_references():
    """Verify NDVI against known analytical calculations.

    Case 1: Healthy vegetation
        NIR = 0.8, Red = 0.2
        NDVI = (0.8 - 0.2) / (0.8 + 0.2) = 0.6 / 1.0 = 0.6000

    Case 2: Dense canopy
        NIR = 0.6, Red = 0.1
        NDVI = (0.6 - 0.1) / (0.6 + 0.1) = 0.5 / 0.7 = 0.7142857...

    Case 3: Soil / Non-vegetated
        NIR = 0.1, Red = 0.2
        NDVI = (0.1 - 0.2) / (0.1 + 0.2) = -0.1 / 0.3 = -0.333333...
    """
    red = np.array([[0.2, 0.1], [0.2, 0.4]], dtype=np.float32)
    nir = np.array([[0.8, 0.6], [0.1, 0.4]], dtype=np.float32)

    ndvi = calculate_ndvi(red, nir)

    # Pixel (0, 0): 0.6000
    assert pytest.approx(ndvi[0, 0], abs=1e-4) == 0.6000

    # Pixel (0, 1): 5/7 ~= 0.7143
    assert pytest.approx(ndvi[0, 1], abs=1e-4) == 5.0 / 7.0

    # Pixel (1, 0): -1/3 ~= -0.3333
    assert pytest.approx(ndvi[1, 0], abs=1e-4) == -1.0 / 3.0

    # Pixel (1, 1): (0.4 - 0.4) / (0.4 + 0.4) = 0.0000
    assert pytest.approx(ndvi[1, 1], abs=1e-4) == 0.0000


def test_ndvi_zero_denominator_safeguard():
    """Verify that zero denominator (NIR + Red == 0) yields NaN without crashing."""
    red = np.array([[0.0, 0.2]], dtype=np.float32)
    nir = np.array([[0.0, 0.8]], dtype=np.float32)

    ndvi = calculate_ndvi(red, nir)

    # Pixel (0, 0) has denominator 0.0 -> must be NaN
    assert np.isnan(ndvi[0, 0])

    # Pixel (0, 1) is valid -> 0.60
    assert pytest.approx(ndvi[0, 1], abs=1e-4) == 0.60


def test_ndvi_nan_and_negative_reflectance():
    """Verify that NaN inputs or physically invalid negative reflectance become NaN."""
    red = np.array([[np.nan, 0.2], [-0.05, 0.1]], dtype=np.float32)
    nir = np.array([[0.8, np.nan], [0.5, 0.7]], dtype=np.float32)

    ndvi = calculate_ndvi(red, nir)

    assert np.isnan(ndvi[0, 0])  # NaN red
    assert np.isnan(ndvi[0, 1])  # NaN nir
    assert np.isnan(ndvi[1, 0])  # Negative red (-0.05 is unphysical)
    assert pytest.approx(ndvi[1, 1], abs=1e-4) == 6.0 / 8.0  # (0.7 - 0.1) / (0.7 + 0.1) = 0.75


def test_ndvi_sentinel2_integer_scaling():
    """Verify auto-detection and handling of Sentinel-2 L2A 10,000 integer scaling."""
    # Scaled integers: 8000 -> 0.8 reflectance, 2000 -> 0.2 reflectance
    red_s2 = np.array([[2000]], dtype=np.int32)
    nir_s2 = np.array([[8000]], dtype=np.int32)

    ndvi = calculate_ndvi(red_s2, nir_s2)

    assert pytest.approx(ndvi[0, 0], abs=1e-4) == 0.6000


def test_ndvi_mismatched_shapes_raise_error():
    """Verify ValueError is raised when Red and NIR array shapes differ."""
    red = np.zeros((3, 3), dtype=np.float32)
    nir = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="shapes must match"):
        calculate_ndvi(red, nir)


def test_ndvi_empty_array_raises_error():
    """Verify ValueError is raised on empty input arrays."""
    red = np.empty((0, 0), dtype=np.float32)
    nir = np.empty((0, 0), dtype=np.float32)

    with pytest.raises(ValueError, match="empty arrays"):
        calculate_ndvi(red, nir)


def test_ndmi_calculation_with_swir1():
    """Verify NDMI calculation from NIR and SWIR1 bands: (NIR - SWIR1) / (NIR + SWIR1)."""
    # Healthy canopy: high NIR, moderate SWIR1 absorption
    nir = np.array([[0.6, 0.5]], dtype=np.float32)
    swir1 = np.array([[0.2, 0.5]], dtype=np.float32)

    ndmi = calculate_ndmi(nir, swir1)

    # (0.6 - 0.2) / (0.6 + 0.2) = 0.4 / 0.8 = 0.5000
    assert pytest.approx(ndmi[0, 0], abs=1e-4) == 0.5000

    # (0.5 - 0.5) / (0.5 + 0.5) = 0.0000
    assert pytest.approx(ndmi[0, 1], abs=1e-4) == 0.0000


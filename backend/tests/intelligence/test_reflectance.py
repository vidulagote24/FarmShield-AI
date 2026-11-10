"""Tests for source-aware Sentinel-2 reflectance calibration and harmonization.

Tests cover:
- Harmonized SR (GEE S2_SR_HARMONIZED)
- Raw L2A DN with PB >= 04.00 (BOA_ADD_OFFSET = -1000)
- Raw L2A DN with PB < 04.00 (BOA_ADD_OFFSET = 0)
- Normalized float reflectance
- Double-offset guardrail
- NoData handling (DN = 0)
- High plausible reflectance (> 1.0)
- Small atmospheric over-correction negative handling
"""

import numpy as np
import pytest

from backend.app.intelligence.geospatial.reflectance import (
    S2CalibrationMetadata,
    S2ReflectanceMode,
    calibrate_sentinel2_reflectance,
)


def test_harmonized_sr_mode():
    """Verify Harmonized Surface Reflectance (e.g. GEE COPERNICUS/S2_SR_HARMONIZED)."""
    # GEE Harmonized SR: DN = 10000 -> SR = 1.0, DN = 0 -> NoData
    raw_array = np.array([
        [2000, 8000],
        [0, 12500],  # 0 is NoData, 12500 is 1.25 (bright dry surface / salt)
    ], dtype=np.int32)

    meta = S2CalibrationMetadata(mode=S2ReflectanceMode.HARMONIZED_SR)
    sr = calibrate_sentinel2_reflectance(raw_array, meta)

    # Pixel (0, 0): 2000 / 10000 = 0.2000
    assert pytest.approx(sr[0, 0], abs=1e-4) == 0.2000

    # Pixel (0, 1): 8000 / 10000 = 0.8000
    assert pytest.approx(sr[0, 1], abs=1e-4) == 0.8000

    # Pixel (1, 0): DN = 0 is NoData -> must be NaN
    assert np.isnan(sr[1, 0])

    # Pixel (1, 1): 12500 / 10000 = 1.2500 (plausible bright surface > 1.0 preserved)
    assert pytest.approx(sr[1, 1], abs=1e-4) == 1.2500


def test_raw_l2a_dn_baseline_after_jan_2022():
    """Verify Raw Sentinel-2 L2A DN with PB >= 04.00 (BOA_ADD_OFFSET = -1000).

    Formula: SR = (DN - 1000) / 10000.0
    """
    raw_dn = np.array([
        [3000, 1000],  # 3000 -> 0.20, 1000 -> 0.00
        [900, 400],    # 900 -> -0.01 (small negative), 400 -> -0.06 (severely negative)
        [0, 11000],    # 0 -> NoData, 11000 -> 1.00
    ], dtype=np.int32)

    meta = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        processing_baseline="04.00",
        boa_add_offset=-1000.0,
    )
    sr = calibrate_sentinel2_reflectance(raw_dn, meta)

    # (3000 - 1000) / 10000 = 0.2000
    assert pytest.approx(sr[0, 0], abs=1e-4) == 0.2000

    # (1000 - 1000) / 10000 = 0.0000
    assert pytest.approx(sr[0, 1], abs=1e-4) == 0.0000

    # (900 - 1000) / 10000 = -0.0100 (atmospheric over-correction within tolerance -0.05 -> clamped to 0.0)
    assert pytest.approx(sr[1, 0], abs=1e-4) == 0.0000

    # (400 - 1000) / 10000 = -0.0600 (severely negative -> invalid / NaN)
    assert np.isnan(sr[1, 1])

    # DN = 0 is NoData -> NaN
    assert np.isnan(sr[2, 0])

    # (11000 - 1000) / 10000 = 1.0000
    assert pytest.approx(sr[2, 1], abs=1e-4) == 1.0000


def test_raw_l2a_dn_legacy_baseline():
    """Verify Raw Sentinel-2 L2A DN with PB < 04.00 (BOA_ADD_OFFSET = 0)."""
    raw_dn = np.array([[2500, 0]], dtype=np.int32)
    meta = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        processing_baseline="02.14",
        boa_add_offset=0.0,
    )
    sr = calibrate_sentinel2_reflectance(raw_dn, meta)

    assert pytest.approx(sr[0, 0], abs=1e-4) == 0.2500
    assert np.isnan(sr[0, 1])


def test_normalized_float_mode():
    """Verify normalized float mode pass-through and validation."""
    float_array = np.array([
        [0.45, 1.15],
        [-0.02, 2.5],  # -0.02 within tolerance, 2.5 exceeds max plausible (2.0)
    ], dtype=np.float32)

    meta = S2CalibrationMetadata(mode=S2ReflectanceMode.NORMALIZED_FLOAT)
    sr = calibrate_sentinel2_reflectance(float_array, meta)

    assert pytest.approx(sr[0, 0], abs=1e-4) == 0.45
    assert pytest.approx(sr[0, 1], abs=1e-4) == 1.15
    assert pytest.approx(sr[1, 0], abs=1e-4) == 0.0  # Clamped small negative
    assert np.isnan(sr[1, 1])  # Over max plausible 2.0 -> NaN


def test_guardrail_against_double_offset():
    """Verify ValueError is raised if raw offset is applied to an already float reflectance array."""
    float_array = np.array([[0.20, 0.80]], dtype=np.float32)

    # Erroneous attempt to apply raw offset to already normalized data
    meta = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=-1000.0,
    )

    with pytest.raises(ValueError, match="already contain normalized float"):
        calibrate_sentinel2_reflectance(float_array, meta)


def test_guardrail_against_silent_guessing_of_offset():
    """Verify ValueError is raised if RAW_L2A_DN is requested without offset or baseline."""
    raw_array = np.array([[2000]], dtype=np.int32)
    meta = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=None,
        processing_baseline=None,
    )

    with pytest.raises(ValueError, match="Cannot silently infer"):
        calibrate_sentinel2_reflectance(raw_array, meta)


def test_configurable_negative_reflectance_modes():
    """Verify configurable handling of small negative reflectances (unclamped vs masked)."""
    # 900 DN with offset -1000 -> -0.0100 (atmospheric over-correction)
    raw_dn = np.array([[900]], dtype=np.int32)

    # 1. allow_negative_reflectance=True: preserves exact negative value
    meta_allow = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=-1000.0,
        allow_negative_reflectance=True,
    )
    sr_allow = calibrate_sentinel2_reflectance(raw_dn, meta_allow)
    assert pytest.approx(sr_allow[0, 0], abs=1e-4) == -0.0100

    # 2. clamp_small_negatives=False and allow=False: masks negative value as NaN
    meta_strict = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=-1000.0,
        clamp_small_negatives=False,
        allow_negative_reflectance=False,
    )
    sr_strict = calibrate_sentinel2_reflectance(raw_dn, meta_strict)
    assert np.isnan(sr_strict[0, 0])


def test_configurable_max_plausible_reflectance():
    """Verify configurable upper physical reflectance validity limit."""
    # 13000 DN with offset 0 -> 1.3000 reflectance
    raw_dn = np.array([[13000, 11000]], dtype=np.int32)

    # Standard threshold 2.0 allows both
    meta_standard = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=0.0,
        max_plausible_reflectance=2.0,
    )
    sr_std = calibrate_sentinel2_reflectance(raw_dn, meta_standard)
    assert pytest.approx(sr_std[0, 0], abs=1e-4) == 1.3000
    assert pytest.approx(sr_std[0, 1], abs=1e-4) == 1.1000

    # Strict threshold 1.20 masks 1.30 as NaN, keeps 1.10
    meta_strict = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=0.0,
        max_plausible_reflectance=1.20,
    )
    sr_strict = calibrate_sentinel2_reflectance(raw_dn, meta_strict)
    assert np.isnan(sr_strict[0, 0])
    assert pytest.approx(sr_strict[0, 1], abs=1e-4) == 1.1000


def test_calibration_diagnostics_preserves_metadata():
    """Verify calibrate_sentinel2_reflectance_with_diagnostics preserves metadata and counts."""
    from backend.app.intelligence.geospatial.reflectance import (
        calibrate_sentinel2_reflectance_with_diagnostics,
    )

    raw_dn = np.array([
        [0, 3000],       # 0 is NoData, 3000 -> 0.20
        [900, 25000],    # 900 -> clamped from -0.01 to 0.0, 25000 -> 2.4 (exceeds max 2.0)
    ], dtype=np.int32)

    meta = S2CalibrationMetadata(
        mode=S2ReflectanceMode.RAW_L2A_DN,
        boa_add_offset=-1000.0,
        max_plausible_reflectance=2.0,
        clamp_small_negatives=True,
    )

    diag = calibrate_sentinel2_reflectance_with_diagnostics(raw_dn, meta)

    assert diag.applied_offset == -1000.0
    assert diag.applied_scale == 10000.0
    assert diag.nodata_pixel_count == 1
    assert diag.clamped_negative_count == 1
    assert diag.exceeded_max_count == 1
    assert diag.valid_pixel_count == 2
    assert diag.metadata.mode == S2ReflectanceMode.RAW_L2A_DN


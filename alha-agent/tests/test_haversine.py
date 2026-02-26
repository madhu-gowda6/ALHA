"""Tests for utils.haversine — great-circle distance calculation."""
import math

import pytest

from utils.haversine import haversine_km


class TestHaversineKm:
    def test_same_point_returns_zero(self):
        assert haversine_km(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_known_distance_delhi_to_lucknow(self):
        # Delhi: 28.6139, 77.2090 | Lucknow: 26.8467, 80.9462
        # ~417 km great-circle distance
        dist = haversine_km(28.6139, 77.2090, 26.8467, 80.9462)
        assert 410 < dist < 425

    def test_known_distance_jaipur_to_ahmedabad(self):
        # Jaipur: 26.9124, 75.7873 | Ahmedabad: 23.0225, 72.5714 → ~529 km
        dist = haversine_km(26.9124, 75.7873, 23.0225, 72.5714)
        assert 510 < dist < 550

    def test_symmetry(self):
        d1 = haversine_km(28.0, 77.0, 26.0, 80.0)
        d2 = haversine_km(26.0, 80.0, 28.0, 77.0)
        assert abs(d1 - d2) < 0.001

    def test_returns_float(self):
        result = haversine_km(10.0, 20.0, 30.0, 40.0)
        assert isinstance(result, float)

    def test_positive_distance(self):
        result = haversine_km(10.0, 20.0, 30.0, 40.0)
        assert result > 0

    def test_equatorial_degree_approx_111km(self):
        # 1 degree of longitude at equator ≈ 111.32 km
        dist = haversine_km(0.0, 0.0, 0.0, 1.0)
        assert abs(dist - 111.32) < 1.0

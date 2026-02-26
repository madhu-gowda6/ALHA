"""Tests for tools.find_nearest_vet stub."""
import inspect

import pytest

from tools.find_nearest_vet import find_nearest_vet


class TestFindNearestVet:
    @pytest.mark.asyncio
    async def test_find_nearest_vet_is_async(self):
        assert inspect.iscoroutinefunction(find_nearest_vet)

    def test_find_nearest_vet_accepts_required_args(self):
        sig = inspect.signature(find_nearest_vet)
        params = list(sig.parameters.keys())
        assert "session_id" in params
        assert "farmer_lat" in params
        assert "farmer_lon" in params
        assert "animal_type" in params

    def test_find_nearest_vet_module_importable(self):
        from tools import find_nearest_vet as mod
        assert mod is not None

"""Tests for tools.save_consultation stub."""
import inspect

import pytest

from tools.save_consultation import save_consultation


class TestSaveConsultation:
    @pytest.mark.asyncio
    async def test_save_consultation_is_async(self):
        assert inspect.iscoroutinefunction(save_consultation)

    def test_save_consultation_accepts_required_args(self):
        sig = inspect.signature(save_consultation)
        params = list(sig.parameters.keys())
        required = [
            "session_id",
            "farmer_phone",
            "animal_type",
            "disease_name",
            "severity",
            "treatment_summary",
        ]
        for param in required:
            assert param in params, f"Missing parameter: {param}"

    def test_save_consultation_module_importable(self):
        from tools import save_consultation as mod
        assert mod is not None

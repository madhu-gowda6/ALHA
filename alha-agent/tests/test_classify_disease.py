"""Tests for tools.classify_disease stub."""
import pytest

from tools.classify_disease import classify_disease


class TestClassifyDisease:
    @pytest.mark.asyncio
    async def test_classify_disease_is_async(self):
        import inspect
        assert inspect.iscoroutinefunction(classify_disease)

    @pytest.mark.asyncio
    async def test_classify_disease_accepts_required_args(self):
        import inspect
        sig = inspect.signature(classify_disease)
        params = list(sig.parameters.keys())
        assert "session_id" in params
        assert "s3_image_key" in params
        assert "animal_type" in params

    def test_classify_disease_module_importable(self):
        from tools import classify_disease as mod
        assert mod is not None

"""Tests for hooks.pii_filter_hook — phone number redaction."""
import pytest

from hooks.pii_filter_hook import redact_phone, PIIFilterHook


class TestRedactPhone:
    def test_redacts_e164_with_plus(self):
        assert redact_phone("+919000000001") == "+91XXXXX0001"

    def test_redacts_e164_without_plus(self):
        assert redact_phone("919000000001") == "+91XXXXX0001"

    def test_redacts_local_10_digit(self):
        assert redact_phone("9000000001") == "+91XXXXX0001"

    def test_redacts_local_6xx_number(self):
        assert redact_phone("6000000001") == "+91XXXXX0001"

    def test_does_not_redact_non_phone(self):
        assert redact_phone("hello world") == "hello world"

    def test_redacts_phone_embedded_in_text(self):
        result = redact_phone("Call 9000000001 now")
        assert "9000000001" not in result
        assert "+91XXXXX0001" in result

    def test_non_phone_digits_unchanged(self):
        assert redact_phone("12345") == "12345"

    def test_last_four_digits_preserved(self):
        # AC #10: last 4 digits visible for vet callback (+91XXXXX1234)
        assert redact_phone("+919876541234") == "+91XXXXX1234"


class TestPIIFilterHook:
    @pytest.mark.asyncio
    async def test_redacts_phone_key(self):
        hook = PIIFilterHook()
        result = await hook.pre_tool_use(
            session_id="s1",
            tool_name="send_notification",
            tool_input={"vet_phone": "+919100000001", "farmer_name": "Raju"},
        )
        assert result["vet_phone"] == "+91XXXXX0001"
        assert result["farmer_name"] == "Raju"

    @pytest.mark.asyncio
    async def test_non_phone_keys_unchanged(self):
        hook = PIIFilterHook()
        result = await hook.pre_tool_use(
            session_id="s1",
            tool_name="classify_disease",
            tool_input={"animal_type": "cattle", "session_id": "abc"},
        )
        assert result["animal_type"] == "cattle"

"""Tests for tools.find_nearest_vet — haversine ordering, filtering, and soft failures."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError

from tools.find_nearest_vet import find_nearest_vet
from utils.haversine import haversine_km


def _vet_item(vet_id: str, name: str, phone: str, speciality: str,
              lat: float, lon: float, district: str = "Test") -> dict:
    """Build a DynamoDB-format vet item."""
    return {
        "vet_id": {"S": vet_id},
        "name": {"S": name},
        "phone": {"S": phone},
        "speciality": {"S": speciality},
        "lat": {"N": str(lat)},
        "lon": {"N": str(lon)},
        "district": {"S": district},
        "state": {"S": "Maharashtra"},
    }


class TestFindNearestVetToolMeta:
    def test_tool_has_name(self):
        assert find_nearest_vet.name == "find_nearest_vet"

    def test_tool_has_description(self):
        assert len(find_nearest_vet.description) > 0

    def test_tool_schema_has_required_fields(self):
        schema = find_nearest_vet.input_schema
        required = schema.get("required", [])
        assert "session_id" in required
        assert "lat" in required
        assert "lon" in required
        assert "animal_type" in required

    def test_tool_module_importable(self):
        from tools import find_nearest_vet as mod
        assert mod is not None


class TestFindNearestVetHappyPath:
    @pytest.mark.asyncio
    async def test_closest_vet_returned_by_haversine(self):
        """Three cattle vets — the one nearest to farmer should be returned."""
        vets = [
            _vet_item("v1", "Dr. Far", "+910001", "cattle", 20.0, 75.0),
            _vet_item("v2", "Dr. Near", "+910002", "cattle", 18.52, 73.86),
            _vet_item("v3", "Dr. Mid", "+910003", "cattle", 19.0, 74.0),
        ]
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.return_value = {"Items": vets}
            result = await find_nearest_vet.handler({
                "session_id": "s1",
                "lat": 18.5204,
                "lon": 73.8567,
                "animal_type": "cattle",
            })

        content = json.loads(result["content"][0]["text"])
        assert content["name"] == "Dr. Near"
        assert content["distance_km"] < 5.0

    @pytest.mark.asyncio
    async def test_animal_type_filter_applied(self):
        vets = [
            _vet_item("v1", "Cattle Vet", "+910001", "cattle", 18.5204, 73.8567),
            _vet_item("v2", "Poultry Vet", "+910002", "poultry", 18.5200, 73.8560),
        ]
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.return_value = {"Items": vets}
            result = await find_nearest_vet.handler({
                "session_id": "s2",
                "lat": 18.5204,
                "lon": 73.8567,
                "animal_type": "cattle",
            })

        content = json.loads(result["content"][0]["text"])
        assert content["name"] == "Cattle Vet"
        assert "error" not in content

    @pytest.mark.asyncio
    async def test_haversine_distance_ordering_with_known_vectors(self):
        """Jaipur is closer to Delhi than Lucknow — ordering must reflect this."""
        vets = [
            _vet_item("v1", "Lucknow Vet", "+910001", "cattle", 26.8467, 80.9462),
            _vet_item("v2", "Jaipur Vet", "+910002", "cattle", 26.9124, 75.7873),
        ]
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.return_value = {"Items": vets}
            result = await find_nearest_vet.handler({
                "session_id": "s3",
                "lat": 28.6139,
                "lon": 77.2090,
                "animal_type": "cattle",
            })

        content = json.loads(result["content"][0]["text"])
        assert content["name"] == "Jaipur Vet"

    @pytest.mark.asyncio
    async def test_vet_found_ws_message_dispatched(self):
        mock_ws = AsyncMock()
        vets = [_vet_item("v1", "Dr. Test", "+910001", "cattle", 18.52, 73.86)]
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {"s4": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            mock_ddb.scan.return_value = {"Items": vets}
            await find_nearest_vet.handler({
                "session_id": "s4",
                "lat": 18.5204,
                "lon": 73.8567,
                "animal_type": "cattle",
            })
            await asyncio.sleep(0)

        mock_ws.send_json.assert_called_once()
        payload = mock_ws.send_json.call_args[0][0]
        assert payload["type"] == "vet_found"
        assert payload["name"] == "Dr. Test"


class TestFindNearestVetSoftFailures:
    @pytest.mark.asyncio
    async def test_no_vet_for_animal_type_returns_no_vet_found(self):
        vets = [_vet_item("v1", "Cattle Vet", "+910001", "cattle", 18.5, 73.8)]
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.return_value = {"Items": vets}
            result = await find_nearest_vet.handler({
                "session_id": "s5",
                "lat": 18.5204,
                "lon": 73.8567,
                "animal_type": "poultry",
            })

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "NO_VET_FOUND"
        assert "message" in content
        assert "message_hi" in content

    @pytest.mark.asyncio
    async def test_client_error_returns_structured_error(self):
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.side_effect = ClientError(
                error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                operation_name="Scan",
            )
            result = await find_nearest_vet.handler({
                "session_id": "s6",
                "lat": 18.5204,
                "lon": 73.8567,
                "animal_type": "cattle",
            })

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "VET_SEARCH_ERROR"
        assert "content" in result

    @pytest.mark.asyncio
    async def test_client_error_does_not_raise_exception(self):
        with (
            patch("tools.find_nearest_vet._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.scan.side_effect = ClientError(
                error_response={"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
                operation_name="Scan",
            )
            result = await find_nearest_vet.handler({
                "session_id": "s7",
                "lat": 18.0,
                "lon": 73.0,
                "animal_type": "cattle",
            })
        assert "content" in result

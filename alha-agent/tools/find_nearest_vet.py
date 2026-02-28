"""Tool: find_nearest_vet — locate nearest available vet via DynamoDB + haversine."""
import asyncio
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError
from claude_agent_sdk import tool

from config import config
from utils.haversine import haversine_km

log = structlog.get_logger()

# Module-level DynamoDB client
_dynamodb = boto3.client("dynamodb", region_name=config.aws_region)


@tool(
    "find_nearest_vet",
    "Search the alha-vets DynamoDB table for the closest veterinarian matching the animal type. "
    "Uses haversine distance on GPS coordinates. Returns vet name, phone, distance, and location.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active consultation session ID"},
            "lat": {"type": "number", "description": "Farmer latitude (decimal degrees)"},
            "lon": {"type": "number", "description": "Farmer longitude (decimal degrees)"},
            "animal_type": {
                "type": "string",
                "description": "Animal species to match vet speciality: cattle, poultry, buffalo",
            },
        },
        "required": ["session_id", "lat", "lon", "animal_type"],
    },
)
async def find_nearest_vet(args: dict) -> dict:
    """Scan alha-vets, compute haversine distances, return closest vet matching animal_type."""
    session_id = args.get("session_id", "")
    lat = float(args.get("lat", 0.0))
    lon = float(args.get("lon", 0.0))
    animal_type = args.get("animal_type", "cattle")

    try:
        # Paginated scan — DynamoDB returns max 1MB per call; iterate until exhausted.
        vets: list[dict] = []
        scan_kwargs: dict = {"TableName": config.vets_table}
        while True:
            response = _dynamodb.scan(**scan_kwargs)
            vets.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        # Filter by speciality
        matching = [v for v in vets if v.get("speciality", {}).get("S", "") == animal_type]

        if not matching:
            result = {
                "error": True,
                "code": "NO_VET_FOUND",
                "message": f"No vet found for animal type: {animal_type}.",
                "message_hi": f"{animal_type} पशु के लिए कोई पशु चिकित्सक नहीं मिला।",
                "session_id": session_id,
            }
            log.warning(
                "no_vet_found",
                tool_name="find_nearest_vet",
                session_id=session_id,
                animal_type=animal_type,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        # Compute haversine distance for each matching vet
        for vet in matching:
            vet_lat = float(vet["lat"]["N"])
            vet_lon = float(vet["lon"]["N"])
            vet["_distance_km"] = haversine_km(lat, lon, vet_lat, vet_lon)

        matching.sort(key=lambda v: v["_distance_km"])
        top = matching[0]

        vet_id = top.get("vet_id", {}).get("S", "")
        vet_name = top.get("name", {}).get("S", "")
        vet_phone = top.get("phone", {}).get("S", "")
        vet_speciality = top.get("speciality", {}).get("S", "")
        distance_km = round(top["_distance_km"], 2)
        vet_lat_out = float(top["lat"]["N"])
        vet_lon_out = float(top["lon"]["N"])

        log.info(
            "tool_executed",
            tool_name="find_nearest_vet",
            session_id=session_id,
            animal_type=animal_type,
            distance_km=distance_km,
            vet_id=vet_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Send vet_found WS message to Flutter
        from ws_map import _active_ws_map

        ws = _active_ws_map.get(session_id)
        if ws:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": "vet_found",
                        "name": vet_name,
                        "speciality": vet_speciality,
                        "distance_km": distance_km,
                        "phone": vet_phone,
                        "session_id": session_id,
                    }
                )
            )

        result = {
            "vet_id": vet_id,
            "name": vet_name,
            "speciality": vet_speciality,
            "distance_km": distance_km,
            "phone": vet_phone,
            "lat": vet_lat_out,
            "lon": vet_lon_out,
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except ClientError as exc:
        log.error(
            "dynamo_scan_error",
            tool_name="find_nearest_vet",
            session_id=session_id,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        result = {
            "error": True,
            "code": "VET_SEARCH_ERROR",
            "message": "Vet search failed. Please try again.",
            "message_hi": "पशु चिकित्सक खोज विफल रही। कृपया पुनः प्रयास करें।",
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

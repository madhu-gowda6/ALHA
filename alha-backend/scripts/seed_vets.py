"""
Seed vet records into alha-vets DynamoDB table.

Usage:
    python scripts/seed_vets.py
"""
import os
import sys
from decimal import Decimal

import boto3
import structlog

log = structlog.get_logger()

DEMO_VETS = [
    {
        "vet_id": "vet-001",
        "name": "Dr. Ramesh Gupta",
        "phone": "+919100000001",
        "speciality": "cattle",
        "lat": 12.8720,
        "lon": 77.6513,
        "district": "Bengaluru",
        "state": "Karnataka",
    },
    {
        "vet_id": "vet-002",
        "name": "Dr. Madhu Gowda",
        "phone": "+919100000002",
        "speciality": "poultry",
        "lat": 12.8697,
        "lon": 77.6580,
        "district": "Bengaluru",
        "state": "Karnataka",
    },
    {
        "vet_id": "vet-003",
        "name": "Dr. Arjun Patel",
        "phone": "+919100000003",
        "speciality": "buffalo",
        "lat": 23.0225,
        "lon": 72.5714,
        "district": "Ahmedabad",
        "state": "Gujarat",
    },
]


def seed_vets(table_name: str, region: str = "us-east-1") -> None:
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    for vet in DEMO_VETS:
        item = dict(vet)
        item["lat"] = Decimal(str(vet["lat"]))
        item["lon"] = Decimal(str(vet["lon"]))
        table.put_item(Item=item)
        log.info("vet_seeded", vet_id=vet["vet_id"], name=vet["name"])

    log.info("seed_complete", vet_count=len(DEMO_VETS))


def main() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    table_name = os.environ.get("VETS_TABLE", "alha-vets")
    seed_vets(table_name=table_name, region=region)


if __name__ == "__main__":
    main()

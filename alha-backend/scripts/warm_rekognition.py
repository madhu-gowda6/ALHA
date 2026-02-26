"""
Warm Rekognition Custom Labels models (start inference endpoints).

Usage:
    python scripts/warm_rekognition.py
"""
import os
import sys

import boto3
import structlog

log = structlog.get_logger()


def warm_model(client, project_version_arn: str, min_units: int = 1) -> None:
    try:
        client.start_project_version(
            ProjectVersionArn=project_version_arn,
            MinInferenceUnits=min_units,
        )
        log.info("model_warmed", arn=project_version_arn)
    except client.exceptions.ResourceInUseException:
        log.info("model_already_running", arn=project_version_arn)


def main() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    cattle_arn = os.environ.get("REKOGNITION_CATTLE_ARN")
    poultry_arn = os.environ.get("REKOGNITION_POULTRY_ARN")

    if not cattle_arn or not poultry_arn:
        log.error(
            "missing_env_vars",
            message="Set REKOGNITION_CATTLE_ARN and REKOGNITION_POULTRY_ARN",
            message_hi="REKOGNITION_CATTLE_ARN और REKOGNITION_POULTRY_ARN सेट करें",
        )
        sys.exit(1)

    client = boto3.client("rekognition", region_name=region)
    warm_model(client, cattle_arn)
    warm_model(client, poultry_arn)


if __name__ == "__main__":
    main()

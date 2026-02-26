"""Tool: classify_disease — run Rekognition custom labels on uploaded image."""
import os

import boto3
import structlog

log = structlog.get_logger()


async def classify_disease(session_id: str, s3_image_key: str, animal_type: str) -> dict:
    """
    Classify disease from an S3 image using Rekognition Custom Labels.

    Args:
        session_id: Active consultation session ID.
        s3_image_key: S3 object key for the uploaded image.
        animal_type: One of 'cattle', 'poultry', 'buffalo'.

    Returns:
        dict with disease_name, confidence_score, bounding_boxes.
    """
    pass

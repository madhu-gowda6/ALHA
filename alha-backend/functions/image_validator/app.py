import json
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

_s3 = boto3.client("s3")


def handler(event, context):
    """Generate a pre-signed S3 PUT URL for image upload.

    Expects: POST /api/upload-url
    Body (optional): {"session_id": "<value>"}
    Auth: Cognito JWT (claims injected by API GW authorizer)
    """
    # Prefer session_id from JWT sub claim (Cognito HTTP API authorizer)
    session_id = None
    try:
        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("jwt", {})
            .get("claims", {})
        )
        session_id = claims.get("sub")
    except Exception:
        pass

    # Fall back to request body
    if not session_id:
        try:
            body = json.loads(event.get("body") or "{}")
            session_id = str(body.get("session_id") or "").strip()
        except Exception:
            pass

    if not session_id:
        session_id = str(uuid4())

    bucket = os.environ.get("S3_IMAGE_BUCKET", "alha-images")
    s3_key = f"uploads/{session_id}/{uuid4()}.jpg"

    try:
        upload_url = _s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": s3_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,  # 15 minutes
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Authorization,Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
            },
            "body": json.dumps({
                "success": True,
                "data": {"upload_url": upload_url, "s3_key": s3_key},
                "error": None,
            }),
        }
    except ClientError as exc:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "success": False,
                "data": None,
                "error": {
                    "code": "PRESIGNED_URL_ERROR",
                    "message": "Could not generate upload URL. Please try again.",
                    "message_hi": "अपलोड URL उत्पन्न नहीं हो सका। कृपया पुनः प्रयास करें।",
                },
            }),
        }

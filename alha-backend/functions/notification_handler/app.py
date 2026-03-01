import json
import os

import boto3

_dynamodb = boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def handler(event, context):
    # Extract farmer_phone from JWT claims (API GW HTTP API v2 format)
    claims = (
        (event or {})
        .get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    farmer_phone = claims.get("phone_number", "")

    if not farmer_phone:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False, "data": None,
                "error": {"message": "Phone number not found in token", "message_hi": "टोकन में फोन नंबर नहीं मिला"},
            }),
        }

    try:
        response = _dynamodb.query(
            TableName=os.environ["CONSULTATIONS_TABLE"],
            IndexName="gsi-farmer-phone",
            KeyConditionExpression="farmer_phone = :phone",
            ExpressionAttributeValues={":phone": {"S": farmer_phone}},
            ScanIndexForward=False,  # no-op (GSI has no sort key); app sort below
        )
        items = response.get("Items", [])
        consultations = []
        for item in items:
            consultations.append({
                "consultation_id": item.get("session_id", {}).get("S", ""),
                "animal_type": item.get("animal_type", {}).get("S", ""),
                "disease_name": item.get("disease_name", {}).get("S", ""),
                "confidence_score": float(item.get("confidence_score", {}).get("N", "0")),
                "severity": item.get("severity", {}).get("S", ""),
                "vet_assigned": item.get("vet_assigned", {}).get("S", ""),
                "treatment_summary": item.get("treatment_summary", {}).get("S", ""),
                "kb_citations": item.get("kb_citations", {}).get("S", "[]"),
                "timestamp": item.get("timestamp", {}).get("S", ""),
            })
        # GSI has no sort key — sort by timestamp descending in application
        consultations.sort(key=lambda c: c["timestamp"], reverse=True)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": True, "data": consultations, "error": None}),
        }
    except Exception:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False, "data": None,
                "error": {"message": "Internal server error", "message_hi": "इतिहास लोड करने में त्रुटि"},
            }),
        }


def auth_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    username = body.get("username", "")
    password = body.get("password", "")

    client = boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    try:
        response = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
            ClientId=os.environ["COGNITO_CLIENT_ID"],
        )
        token = response["AuthenticationResult"]["IdToken"]
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": True, "data": {"token": token}, "error": None}),
        }
    except client.exceptions.NotAuthorizedException:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "data": {},
                "error": {
                    "message": "Invalid credentials",
                    "message_hi": "अमान्य प्रमाण-पत्र",
                },
            }),
        }

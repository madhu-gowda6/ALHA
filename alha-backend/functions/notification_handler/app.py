import json
import os

import boto3


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"success": True, "data": [], "error": None}),
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

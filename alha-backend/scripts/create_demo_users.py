"""
Seed 3 demo users into Cognito User Pool for ALHA hackathon demo.

Usage:
    python scripts/create_demo_users.py

Requires:
    - AWS_REGION env var (default: us-east-1)
    - COGNITO_USER_POOL_ID env var
    - AWS credentials with cognito-idp:AdminCreateUser + AdminSetUserPassword
"""
import os
import sys

import boto3
import structlog

log = structlog.get_logger()

DEMO_USERS = [
    {
        "username": "raju",
        "password": "Demo@1234",
        "phone_number": "+919000000001",
        "language_preference": "hi",
        "name": "Raju Singh",
        "animal": "cattle",
    },
    {
        "username": "savita",
        "password": "Demo@1234",
        "phone_number": "+919000000002",
        "language_preference": "hi",
        "name": "Savita Devi",
        "animal": "poultry",
    },
    {
        "username": "deepak",
        "password": "Demo@1234",
        "phone_number": "+919000000003",
        "language_preference": "en",
        "name": "Deepak Kumar",
        "animal": "buffalo",
    },
]


def seed_users(user_pool_id: str, region: str = "us-east-1") -> None:
    client = boto3.client("cognito-idp", region_name=region)

    for user in DEMO_USERS:
        username = user["username"]
        try:
            client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                TemporaryPassword=user["password"],
                UserAttributes=[
                    {"Name": "phone_number", "Value": user["phone_number"]},
                    {"Name": "phone_number_verified", "Value": "true"},
                    {"Name": "custom:language_preference", "Value": user["language_preference"]},
                    {"Name": "name", "Value": user["name"]},
                ],
                MessageAction="SUPPRESS",
            )
            log.info("user_created", username=username)
        except client.exceptions.UsernameExistsException:
            log.info("user_already_exists", username=username)

        client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=user["password"],
            Permanent=True,
        )
        log.info("password_set_permanent", username=username)

    log.info("seed_complete", user_count=len(DEMO_USERS))


def main() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    user_pool_id = os.environ.get("COGNITO_USER_POOL_ID")

    if not user_pool_id:
        log.error(
            "missing_env_var",
            var="COGNITO_USER_POOL_ID",
            message="Set COGNITO_USER_POOL_ID from SAM deploy outputs",
            message_hi="SAM deploy आउटपुट से COGNITO_USER_POOL_ID सेट करें",
        )
        sys.exit(1)

    seed_users(user_pool_id=user_pool_id, region=region)


if __name__ == "__main__":
    main()

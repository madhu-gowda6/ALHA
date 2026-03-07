import os


class Config:
    def __init__(self) -> None:
        self.aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
        self.consultations_table: str = os.environ["CONSULTATIONS_TABLE"]
        self.vets_table: str = os.environ["VETS_TABLE"]
        self.farmers_table: str = os.environ.get("FARMERS_TABLE", "alha-farmers")
        self.disease_models_table: str = os.environ.get("DISEASE_MODELS_TABLE", "alha-disease-models")
        self.s3_image_bucket: str = os.environ["S3_IMAGE_BUCKET"]
        self.rekognition_cattle_arn: str = os.environ.get("REKOGNITION_CATTLE_ARN", "")
        self.rekognition_poultry_arn: str = os.environ.get("REKOGNITION_POULTRY_ARN", "")
        # REKOGNITION_CLAUDE: set true when Rekognition models are unavailable
        # (ARN not configured, or intentionally bypassed). Classification falls through to
        # Claude vision instead — real results, not fake data. Safe to leave enabled in prod
        # until Rekognition models ARNs are set.
        self.rekognition_claude: bool = os.environ.get("REKOGNITION_CLAUDE", "false").lower() == "true"
        self.bedrock_kb_id: str = os.environ.get("BEDROCK_KB_ID", "")
        self.claude_use_bedrock: bool = os.environ.get("CLAUDE_CODE_USE_BEDROCK", "0") == "1"
        self.bedrock_model_id: str = os.environ.get(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
        )
        self.bedrock_vision_model_id: str = os.environ.get(
            "BEDROCK_VISION_MODEL_ID", self.bedrock_model_id
        )
        self.anthropic_custom_headers: str = os.environ.get("ANTHROPIC_CUSTOM_HEADERS", "")
        self.cognito_client_id: str = os.environ.get("COGNITO_CLIENT_ID", "")
        self.cognito_user_pool_id: str = os.environ.get("COGNITO_USER_POOL_ID", "")
        # CORS_ORIGINS: comma-separated list of allowed origins, "*" for dev
        _raw_cors = os.environ.get("CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [o.strip() for o in _raw_cors.split(",")]


config = Config()

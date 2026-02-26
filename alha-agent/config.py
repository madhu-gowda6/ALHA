import os


class Config:
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    consultations_table: str = os.environ["CONSULTATIONS_TABLE"]
    vets_table: str = os.environ["VETS_TABLE"]
    farmers_table: str = os.environ.get("FARMERS_TABLE", "alha-farmers")
    disease_models_table: str = os.environ.get("DISEASE_MODELS_TABLE", "alha-disease-models")
    s3_image_bucket: str = os.environ["S3_IMAGE_BUCKET"]
    rekognition_cattle_arn: str = os.environ.get("REKOGNITION_CATTLE_ARN", "")
    rekognition_poultry_arn: str = os.environ.get("REKOGNITION_POULTRY_ARN", "")
    bedrock_kb_id: str = os.environ.get("BEDROCK_KB_ID", "")
    claude_use_bedrock: bool = os.environ.get("CLAUDE_CODE_USE_BEDROCK", "0") == "1"
    anthropic_custom_headers: str = os.environ.get("ANTHROPIC_CUSTOM_HEADERS", "")


config = Config()

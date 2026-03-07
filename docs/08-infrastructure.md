# Infrastructure

## Overview

ALHA uses AWS SAM (`alha-backend/template.yaml`) to define all infrastructure as code. A hybrid serverless architecture: Lambda for REST endpoints, ECS Fargate for the stateful WebSocket agent.

---

## Network Architecture

```
Internet
    │
    ▼
CloudFront Distribution
    ├── Default behavior → S3 (Flutter PWA static files)
    └── /ws path pattern → ALB (ECS Fargate agent)
                              │
                    ECS Security Group (port 8000)
                              │
                         ECS Fargate Task
                         (alha-agent:latest)

Internet → API Gateway (HTTP API) → Lambda Functions
```

**VPC:** `10.0.0.0/16`, 2 public subnets across 2 AZs (`10.0.1.0/24`, `10.0.2.0/24`)

---

## AWS Resources

### Compute

| Resource | Type | Config |
|----------|------|--------|
| `AlhaECSCluster` | ECS Cluster | `alha-cluster` |
| `AlhaTaskDefinition` | ECS Task | 0.5 vCPU, 1 GB RAM, Fargate, port 8000 |
| `AlhaECSService` | ECS Service | DesiredCount=1, FARGATE, public IP |
| `ImageValidatorFunction` | Lambda | Python 3.12, arm64, handler: `app.handler` |
| `DiseaseClassifierFunction` | Lambda | Python 3.12, arm64, handler: `app.handler` (stub) |
| `NotificationHandlerFunction` | Lambda | Python 3.12, arm64, handler: `app.handler` |
| `AuthLoginFunction` | Lambda | Python 3.12, arm64, handler: `app.auth_handler` |

### Storage

| Resource | Bucket | Access |
|----------|--------|--------|
| `ImagesBucket` | `alha-images` | Private; CORS allows PUT/GET from `*` |
| `FrontendBucket` | `alha-frontend` | Public static website; S3 website hosting |

### Database (DynamoDB — all PAY_PER_REQUEST)

| Table | PK | GSI |
|-------|----|-----|
| `alha-consultations` | `session_id` (S) | `gsi-farmer-phone` on `farmer_phone` |
| `alha-vets` | `vet_id` (S) | — |
| `alha-farmers` | `phone_number` (S) | — |
| `alha-disease-models` | `animal_type` (S) | — |

### Networking

| Resource | Details |
|----------|---------|
| `AlhaVPC` | `10.0.0.0/16`, DNS enabled |
| `AlhaSubnetA/B` | Public, 2 AZs, `MapPublicIpOnLaunch=true` |
| `AlhaInternetGateway` | Attached to VPC |
| `AlhaALB` | Internet-facing, application type, port 80 |
| `AlhaTargetGroup` | Port 8000, `ip` target type, healthcheck `/health` |
| `ALBSecurityGroup` | Inbound: 80, 443 from `0.0.0.0/0` |
| `ECSSecurityGroup` | Inbound: 8000 from ALB security group only |

### CDN & Auth

| Resource | Details |
|----------|---------|
| `FrontendCloudFront` | Serves S3 static files; `/ws` path → ALB; `https-only`; `PriceClass_100` |
| `CognitoUserPool` | `alha-user-pool`; free-form username; custom attrs: `phone_number`, `language_preference` |
| `CognitoUserPoolClient` | `ALLOW_USER_PASSWORD_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH`, no secret |
| `AlhaHttpApi` | HTTP API v2, Cognito JWT authorizer on all routes |

### ML Services

| Resource | Details |
|----------|---------|
| Rekognition Custom Labels | ARNs configured in `alha-disease-models` DynamoDB table and env vars; models per animal type |
| Bedrock Knowledge Base | `BEDROCK_KB_ID` env var; veterinary documents (ICAR/NDDB) |
| Bedrock Model | `us.anthropic.claude-sonnet-4-6` via Bedrock cross-region inference |

### ECR

| Resource | Details |
|----------|---------|
| `AgentECRRepository` | `alha-agent`; scan on push enabled |
| Image tag | `{account}.dkr.ecr.{region}.amazonaws.com/alha-agent:latest` |

---

## IAM Roles

### `alha-lambda-role` (`LambdaExecutionRole`)
- `AWSLambdaBasicExecutionRole` (managed)
- `dynamodb:*` on all resources
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on all resources
- `cognito-idp:AdminGetUser`, `cognito-idp:AdminInitiateAuth` on all resources

### `alha-ecs-task-role` (`ECSTaskRole`)
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, `bedrock:Retrieve`
- `rekognition:DetectCustomLabels`
- `dynamodb:*`
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`
- `sns:Publish`

### `alha-ecs-execution-role` (`ECSTaskExecutionRole`)
- `AmazonECSTaskExecutionRolePolicy` (managed) — ECR pull, CloudWatch Logs

---

## Environment Variables

### Agent Service (`alha-agent/config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `CONSULTATIONS_TABLE` | **Yes** | — | DynamoDB table name |
| `VETS_TABLE` | **Yes** | — | DynamoDB table name |
| `FARMERS_TABLE` | No | `alha-farmers` | DynamoDB table name |
| `DISEASE_MODELS_TABLE` | No | `alha-disease-models` | DynamoDB table name |
| `S3_IMAGE_BUCKET` | **Yes** | — | S3 bucket for images |
| `REKOGNITION_CATTLE_ARN` | No | `""` | Rekognition model ARN fallback |
| `REKOGNITION_POULTRY_ARN` | No | `""` | Rekognition model ARN fallback |
| `REKOGNITION_CLAUDE` | No | `false` | `true` to skip Rekognition, use Claude vision |
| `BEDROCK_KB_ID` | No | `""` | Bedrock Knowledge Base ID |
| `CLAUDE_CODE_USE_BEDROCK` | No | `0` | `1` to use Bedrock instead of direct API |
| `BEDROCK_MODEL_ID` | No | `us.anthropic.claude-sonnet-4-6` | Bedrock model ID |
| `BEDROCK_VISION_MODEL_ID` | No | *(same as BEDROCK_MODEL_ID)* | Model for image classification |
| `ANTHROPIC_CUSTOM_HEADERS` | No | `""` | Bedrock Guardrail headers |
| `COGNITO_CLIENT_ID` | No | `""` | Cognito app client ID |
| `COGNITO_USER_POOL_ID` | No | `""` | Cognito user pool ID |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |

### Flutter PWA (`alha/lib/config/app_config.dart`)

| `--dart-define` Variable | Default | Description |
|--------------------------|---------|-------------|
| `API_GW_URL` | `https://nwgfpoh71m.execute-api.us-east-1.amazonaws.com/prod` | REST base URL |
| `ALB_DNS` | `alha-alb-1820780785.us-east-1.elb.amazonaws.com` | Direct ALB (non-HTTPS) |
| `COGNITO_CLIENT_ID` | `""` | Cognito client ID |
| `COGNITO_USER_POOL_ID` | `""` | Cognito user pool ID |

WebSocket URL auto-selects: `wss://{host}/ws` (when served via HTTPS/CloudFront) or `ws://{ALB_DNS}/ws` (direct).

---

## CloudWatch Logs

| Log Group | Source | Retention |
|-----------|--------|-----------|
| `/ecs/alha-agent` | ECS Fargate agent | 7 days |

All agent logs use `structlog` JSON format. Every log line includes `session_id` and `timestamp`.

---

## SAM Outputs

| Output Key | Description |
|------------|-------------|
| `ApiGatewayUrl` | API Gateway HTTPS URL |
| `CognitoUserPoolId` | Cognito pool ID |
| `CognitoClientId` | Cognito app client ID |
| `ImagesBucketName` | S3 images bucket |
| `FrontendBucketWebsiteUrl` | S3 static website URL |
| `ALBDNSName` | ALB DNS for direct agent access |
| `ECRRepositoryUri` | ECR URI for Docker image |
| `ECSClusterName` | ECS cluster name |
| `FrontendCloudFrontUrl` | **Primary URL for PWA** (HTTPS — microphone/camera work here) |

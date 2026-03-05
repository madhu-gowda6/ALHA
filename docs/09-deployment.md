# Deployment Guide

## Prerequisites

- AWS CLI configured with IAM permissions for: SAM, Lambda, DynamoDB, S3, Cognito, ECS, ECR, CloudFront, ALB, Rekognition, Bedrock, SNS
- AWS SAM CLI
- Python 3.12
- Flutter 3.x (web support enabled)
- Docker
- `.env` file created from `.env.example`

---

## Step 1: Configure Environment

```bash
cd d:/Hackathon/ALHA
cp .env.example .env
# Edit .env with actual values
```

Required values in `.env`:
```
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
ALB_DNS=alha-alb-xxxx.us-east-1.elb.amazonaws.com
API_GW_URL=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
S3_IMAGE_BUCKET=alha-images
CONSULTATIONS_TABLE=alha-consultations
VETS_TABLE=alha-vets
BEDROCK_KB_ID=XXXXXXXXXX                     # optional, KB must exist
REKOGNITION_CATTLE_ARN=arn:aws:...           # optional, set REKOGNITION_MOCK=true if not available
REKOGNITION_POULTRY_ARN=arn:aws:...          # optional
```

---

## Step 2: Deploy AWS Infrastructure

```bash
cd alha-backend
sam build
sam deploy --guided
```

On first deploy, SAM prompts for:
- Stack name: `alha`
- Region: `us-east-1`
- Stage parameter: `prod`

Save the outputs — you'll need `ApiGatewayUrl`, `CognitoUserPoolId`, `CognitoClientId`, `ALBDNSName`, `FrontendCloudFrontUrl`.

---

## Step 3: Seed Demo Users

```bash
cd alha-backend
python scripts/create_demo_users.py
```

Creates Cognito users:

| Username | Language | Animal |
|----------|----------|--------|
| raju | Hindi | Cattle |
| savita | Hindi | Poultry |
| deepak | English | Buffalo |

---

## Step 4: Seed Vet Data (Optional)

```bash
cd alha-backend
python scripts/seed_vets.py
```

Populates `alha-vets` DynamoDB table with demo veterinarians.

---

## Step 5: Build and Push Agent Docker Image

```bash
cd alha-agent
docker build -t alha-agent .

# Get ECR URI from SAM output
ECR_URI=$(aws cloudformation describe-stacks --stack-name alha \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
  --output text)

aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

docker tag alha-agent:latest $ECR_URI:latest
docker push $ECR_URI:latest
```

ECS Fargate will pull the new image on next task restart. To force update:
```bash
aws ecs update-service --cluster alha-cluster \
  --service alha-agent-service --force-new-deployment
```

---

## Step 6: Build and Deploy Flutter PWA

```bash
cd alha/alha

# Get values from SAM outputs
API_GW_URL="https://xxxx.execute-api.us-east-1.amazonaws.com/prod"

flutter pub get
flutter build web \
  --dart-define=API_GW_URL=$API_GW_URL

# Upload to S3
aws s3 sync build/web/ s3://alha-frontend/ --delete

# Invalidate CloudFront cache
CF_ID=$(aws cloudformation describe-stacks --stack-name alha \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendCloudFrontUrl'].OutputValue" \
  --output text)
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

> **Important:** Always access the PWA via the **CloudFront URL** (HTTPS). Browser microphone and camera APIs require a secure origin. The S3 website URL (`http://`) will not work.

---

## Step 7: Configure Bedrock Knowledge Base (Optional)

1. Create a Bedrock Knowledge Base in the AWS console.
2. Upload ICAR/NDDB veterinary documents to an S3 bucket.
3. Configure the KB to index from that bucket.
4. Add the KB ID to `BEDROCK_KB_ID` environment variable on the ECS task.

---

## Step 8: Configure Rekognition Custom Labels (Optional)

1. Train custom label models for cattle and poultry disease detection.
2. Add model ARNs to `alha-disease-models` DynamoDB table:
   ```bash
   aws dynamodb put-item \
     --table-name alha-disease-models \
     --item '{"animal_type":{"S":"cattle"},"model_arn":{"S":"arn:aws:rekognition:..."}}'
   ```
3. Set `REKOGNITION_MOCK=false` in ECS task environment.

If Rekognition is not configured, set `REKOGNITION_MOCK=true` — the agent falls back to Claude vision for classification.

---

## Step 9: Warm Rekognition Models (If Using)

Rekognition Custom Labels models must be running to use them:

```bash
cd alha-backend
python scripts/warm_rekognition.py
```

---

## Local Development

### Run Agent Locally

```bash
cd alha-agent
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set env vars (from .env)
export CONSULTATIONS_TABLE=alha-consultations
export VETS_TABLE=alha-vets
export S3_IMAGE_BUCKET=alha-images
export AWS_REGION=us-east-1
export REKOGNITION_MOCK=true
export CLAUDE_CODE_USE_BEDROCK=1

uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Run Flutter PWA Locally

```bash
cd alha/alha
flutter pub get
flutter run -d chrome \
  --dart-define=API_GW_URL=http://localhost:8000
```

The WebSocket will connect to `ws://localhost:8000/ws` (non-HTTPS → uses ALB_DNS path, but localhost overrides).

---

## Monitoring

| What to check | Where |
|---------------|-------|
| Agent logs | CloudWatch Logs → `/ecs/alha-agent` |
| Lambda logs | CloudWatch Logs → `/aws/lambda/alha-*` |
| ECS task health | ECS console → `alha-cluster` → `alha-agent-service` |
| ALB health | EC2 console → Target Groups → `alha-tg` → health check `/health` |
| Agent debug | `GET /debug/claude` (development only — remove in production) |

---

## Known Limitations / Production Checklist

- [ ] Remove `GET /debug/claude` endpoint before production deployment
- [ ] Configure SNS SMS in production mode (exit sandbox, verify phone numbers or enable production access)
- [ ] Set `REKOGNITION_MOCK=false` once Rekognition model ARNs are configured
- [ ] Restrict `CORS_ORIGINS` to CloudFront domain (currently `*`)
- [ ] Replace `dynamodb:*` and `s3:*` IAM wildcards with specific resource ARNs
- [ ] Enable DynamoDB encryption at rest (already default in AWS)
- [ ] Set `ANTHROPIC_CUSTOM_HEADERS` with valid Bedrock Guardrail ID
- [ ] Scale ECS service `DesiredCount` for production load
- [ ] Add WAF to CloudFront distribution
- [ ] Enable ALB access logs

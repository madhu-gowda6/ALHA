# ALHA — AI Livestock Health Assistant

Hackathon project: bilingual (Hindi/English) AI-powered veterinary consultation system for Indian farmers.

## Monorepo Structure

```
hackathon/
├── alha/              ← Flutter PWA (Web)
├── alha-agent/        ← Claude Agent SDK service (ECS Fargate)
├── alha-backend/      ← AWS SAM template + Lambda stubs
└── docs/              ← Architecture, API contract, demo script
```

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate IAM permissions
- AWS SAM CLI
- Python 3.12
- Flutter 3.x (web support enabled)
- Docker

### 1. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 2. Deploy AWS Infrastructure

```bash
cd alha-backend
sam build && sam deploy --guided
```

### 3. Seed demo users

```bash
cd alha-backend
python scripts/create_demo_users.py
```

### 4. Build and push agent Docker image

```bash
cd alha-agent
docker build -t alha-agent .
# Push to ECR (see deployment docs)
```

### 5. Run Flutter PWA locally

```bash
cd alha
flutter pub get
flutter run -d chrome
```

## Architecture

See `docs/architecture-diagram.png` and `docs/api-contract.md`.

## Demo Users

| Username | Language | Animal |
|----------|----------|--------|
| raju     | Hindi    | Cattle |
| savita   | Hindi    | Poultry |
| deepak   | English  | Buffalo |

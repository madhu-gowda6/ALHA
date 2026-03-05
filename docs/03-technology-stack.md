# Technology Stack

## Part 1: `alha` — Flutter PWA

| Category | Technology | Version | Notes |
|----------|-----------|---------|-------|
| Language | Dart | >=3.0.0 | |
| Framework | Flutter | 3.x | Web (PWA) target via `dart:html` |
| State Management | flutter_riverpod | ^2.4.0 | `StateNotifierProvider` pattern |
| HTTP Client | http | ^1.2.0 | REST calls to API Gateway |
| WebSocket | web_socket_channel | ^2.4.0 | Persistent connection to agent |
| Local Storage | shared_preferences | ^2.2.0 | Auth token + session ID persistence |
| Image Capture | image_picker | ^1.0.0 | Camera + gallery (web FileInput) |
| Speech-to-Text | speech_to_text | ^6.6.0 | Bilingual: en_US / hi_IN |
| Fonts | google_fonts | ^6.1.0 | Inter + Noto Sans Devanagari |
| Markdown | flutter_markdown | ^0.7.3 | Agent response rendering |
| i18n | intl | ^0.19.0 | Date/time formatting |
| IDs | uuid | ^4.0.0 | Session ID generation |
| Architecture | Component hierarchy | — | `main → Screens → Providers → Services → Widgets` |
| Theme | Material 3 | — | Seed: `#2E7D32` (forest green), background: `#F9F6F0` (cream) |

### Architecture Pattern
Reactive UI over a persistent WebSocket, with Riverpod providers mediating state. Screen triggers tool-invoked overlays (symptom interview, camera, GPS) via `StreamController` event buses. Language detection is auto (Devanagari Unicode range) + user toggle.

---

## Part 2: `alha-agent` — Claude Agent Service

| Category | Technology | Version | Notes |
|----------|-----------|---------|-------|
| Language | Python | 3.11+ (3.12 recommended) | |
| Web Framework | FastAPI | >=0.110.0 | Async ASGI |
| ASGI Server | Uvicorn | >=0.29.0 | With standard extras |
| AI / Agent | claude-agent-sdk | >=0.1.39 | `query()` streaming, MCP in-process server |
| AI Model | Claude Sonnet 4.6 via Bedrock | `us.anthropic.claude-sonnet-4-6` | Bedrock cross-region inference |
| Validation | Pydantic | >=2.6.0 | Request/response models |
| JWT Validation | python-jose | >=3.3.0 | RS256 (Cognito JWKS) |
| Logging | structlog | >=24.1.0 | JSON structured logs → CloudWatch |
| HTTP Client | httpx | >=0.27.0 | Async JWKS fetch |
| AWS SDK | boto3 | >=1.34.0 | DynamoDB, S3, Rekognition, SNS, Bedrock |
| WebSocket | websockets | >=12.0 | Bidirectional JSON framing |
| Container | Docker | — | ECS Fargate, port 8000 |
| Architecture | FastAPI + MCP in-process server | — | 9 tools exposed as MCP tools |

### Architecture Pattern
FastAPI app exposes `/ws` WebSocket endpoint and REST endpoints. The Claude Agent SDK `query()` call drives an agentic loop (max 10 turns) with an in-process MCP server providing 9 tools. Session state (conversation history, language, farmer phone) is held in-memory, per-session asyncio locks prevent concurrent corruption.

---

## Part 3: `alha-backend` — AWS SAM Infrastructure

| Category | Technology | Version | Notes |
|----------|-----------|---------|-------|
| IaC | AWS SAM | 2016-10-31 | Serverless Application Model |
| Runtime | Python | 3.12 on arm64 | All Lambda functions |
| Auth | AWS Cognito | — | User pool with free-form usernames, phone + language custom attributes |
| API | AWS API Gateway HTTP API | — | v2, Cognito JWT authorizer |
| Compute (agent) | AWS ECS Fargate | — | 0.5 vCPU, 1 GB RAM, single task |
| Compute (lambdas) | AWS Lambda | — | 3 functions (image_validator, disease_classifier, notification_handler) |
| Object Storage | AWS S3 | — | `alha-images` (private), `alha-frontend` (public static website) |
| CDN | AWS CloudFront | — | Serves Flutter PWA, routes `/ws` to ALB |
| Database | AWS DynamoDB | — | 4 tables: consultations, vets, farmers, disease-models |
| Load Balancer | AWS ALB | — | Routes HTTP/WS to ECS agent |
| Image ML | AWS Rekognition Custom Labels | — | Per-animal models (cattle, poultry); falls back to Claude vision |
| Knowledge Base | Amazon Bedrock Knowledge Base | — | ICAR/NDDB veterinary documents |
| Notifications | AWS SNS | — | Transactional SMS to farmer + vet |
| Registry | AWS ECR | — | `alha-agent` Docker image |
| Networking | AWS VPC | 10.0.0.0/16 | 2 public subnets across 2 AZs |

### Architecture Pattern
Serverless hybrid: Lambda handles REST (auth, upload URL, history), ECS Fargate handles stateful WebSocket agent. CloudFront provides HTTPS termination and routes `/ws` to ALB → ECS. DynamoDB on-demand billing for all tables.

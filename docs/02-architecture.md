# System Architecture

## Overview

ALHA is a bilingual (Hindi/English) AI-powered veterinary consultation system for Indian farmers. Farmers interact via a Flutter PWA — describing symptoms in text or voice — and receive AI-driven disease diagnosis, treatment guidance, and vet coordination.

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Farmer Device (Browser)"
        PWA["Flutter PWA\n(alha/)"]
    end

    subgraph "AWS CDN"
        CF["CloudFront\n(HTTPS termination)"]
    end

    subgraph "AWS Compute"
        APIGW["API Gateway HTTP API\n(REST endpoints)"]
        ALB["Application Load Balancer\n(WebSocket)"]
        ECS["ECS Fargate\nalha-agent\n(FastAPI + Claude Agent SDK)"]
        L1["Lambda: image_validator\n(GET presigned URL)"]
        L2["Lambda: notification_handler\n(GET history / POST auth)"]
    end

    subgraph "AWS AI/ML"
        CLAUDE["Amazon Bedrock\nClaude Sonnet 4.6"]
        REK["Rekognition\nCustom Labels"]
        KB["Bedrock Knowledge Base\n(ICAR/NDDB docs)"]
    end

    subgraph "AWS Data"
        DDB_C["DynamoDB\nalha-consultations"]
        DDB_V["DynamoDB\nalha-vets"]
        DDB_F["DynamoDB\nalha-farmers"]
        DDB_M["DynamoDB\nalha-disease-models"]
        S3["S3\nalha-images"]
        S3F["S3\nalha-frontend"]
    end

    subgraph "AWS Auth"
        COGNITO["AWS Cognito\nUser Pool"]
    end

    subgraph "Notifications"
        SNS["AWS SNS\n(SMS)"]
    end

    %% PWA connections
    PWA -->|"HTTPS REST"| CF
    PWA -->|"WSS /ws"| CF
    CF -->|"Static files"| S3F
    CF -->|"REST routes"| APIGW
    CF -->|"/ws WebSocket"| ALB

    %% API Gateway
    APIGW -->|"POST /api/auth/login"| L2
    APIGW -->|"POST /api/upload-url"| L1
    APIGW -->|"GET /api/history"| L2

    %% ALB to ECS
    ALB --> ECS

    %% Agent connections
    ECS -->|"authenticate"| COGNITO
    ECS -->|"generate presigned URL"| S3
    ECS -->|"agentic loop"| CLAUDE
    ECS -->|"classify image"| REK
    ECS -->|"query KB"| KB
    ECS -->|"read/write"| DDB_C
    ECS -->|"scan vets"| DDB_V
    ECS -->|"lookup model ARN"| DDB_M
    ECS -->|"SMS"| SNS
    ECS -->|"get image"| S3

    style PWA fill:#E8F5E9
    style ECS fill:#E3F2FD
    style CLAUDE fill:#FFF3E0
```

---

## Consultation Flow Sequence

```mermaid
sequenceDiagram
    actor Farmer as Farmer (PWA)
    participant WS as WebSocket (Agent)
    participant Agent as Claude Agent SDK
    participant Tools as MCP Tools

    Farmer->>WS: {type: "chat", message: "मेरी गाय को बुखार है", language: "hi"}
    WS->>Agent: process_message()
    Agent->>Tools: symptom_interview(session_id, questions, questions_hi)
    Tools-->>WS: {type: "frontend_action", action: "symptom_interview", questions: [...]}
    WS-->>Farmer: Show SymptomInterviewOverlay
    Farmer->>WS: {type: "symptom_answers", answers: [...]}
    WS->>Agent: process_message() with Q&A

    Agent->>Tools: request_image(session_id, prompt, prompt_hi)
    Tools-->>WS: {type: "frontend_action", action: "request_image"}
    WS-->>Farmer: Show CameraOverlay

    Farmer->>WS: [uploads image to S3 via presigned URL]
    Farmer->>WS: {type: "image_data", s3_key: "uploads/..."}
    WS->>Agent: process_message() with s3_key

    Agent->>Tools: classify_disease(s3_key, animal_type)
    Tools-->>WS: {type: "diagnosis", disease: "lumpy_skin_disease", confidence: 87.5}
    WS-->>Farmer: Show ImageBubble with bbox

    Agent->>Tools: query_knowledge_base(disease, animal_type, language)
    Agent->>Tools: assess_severity(disease, animal_type, symptoms)
    Tools-->>WS: {type: "severity", level: "CRITICAL"}
    WS-->>Farmer: Show SeverityBadge (RED)

    Agent->>Tools: request_gps(session_id, prompt, prompt_hi)
    Tools-->>WS: {type: "frontend_action", action: "request_gps"}
    WS-->>Farmer: Show GPS Card

    Farmer->>WS: {type: "gps_data", lat: 28.6, lon: 77.2}
    WS->>Agent: process_message() with GPS

    Agent->>Tools: find_nearest_vet(lat, lon, animal_type)
    Tools-->>WS: {type: "vet_found", name: "Dr. Ramesh", distance_km: 4.7}
    WS-->>Farmer: Show VetCard

    Note over Agent,Tools: CRITICAL: skip vet preference, send immediately
    Agent->>Tools: send_notification(farmer_phone, vet_phone, ...)
    Tools-->>WS: {type: "notification_sent", vet_name: "Dr. Ramesh"}

    Agent->>Tools: save_consultation(all fields)
    Tools-->>WS: {type: "session_complete", consultation_id: "uuid"}
    WS-->>Farmer: Show "New Consultation" banner

    Note over WS,Agent: Streaming tokens sent via {type: "token"} throughout
```

---

## Key Design Decisions

### 1. Persistent WebSocket for Agentic Interaction
REST APIs cannot support multi-turn agentic interactions where the agent waits for user input mid-flow (symptom answers, image upload, GPS). A persistent WebSocket allows bidirectional, interruptible communication between the Claude agent and the Flutter UI.

### 2. In-Process MCP Server
Tools are registered as an in-process MCP server (not a separate process) to avoid subprocess IPC latency. This keeps the architecture simple while preserving MCP protocol compatibility.

### 3. Hybrid Serverless Architecture
- **Lambda** handles stateless REST operations (auth, upload URL, history).
- **ECS Fargate** handles the stateful WebSocket agent. Lambda cold starts and 15-minute execution limits make it unsuitable for long-running WebSocket connections.

### 4. Claude Agent SDK with Bedrock
The `query()` streaming API with `stream_input()` (async iterable prompt) keeps stdin open for bidirectional MCP I/O. The subprocess environment inherits ECS IAM credential env vars (`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`) for seamless Bedrock access without explicit API keys.

### 5. Dual Disease Classification
Rekognition Custom Labels provides fast, specialized detection. Claude vision acts as a double-check. On disagreement, Claude wins (more generalizable). On Rekognition error, Claude is the sole fallback. `REKOGNITION_MOCK=true` bypasses Rekognition entirely for development without Rekognition model ARNs.

### 6. Language Handling
Language is detected per-message from Devanagari Unicode range (`\u0900–\u097F`) in Flutter and tagged via `[language: hi/en]` in every prompt. The system prompt mandates strict language consistency — no mixing within a session.

### 7. CloudFront WebSocket Routing
Chrome blocks mixed-content WebSocket connections (`ws://` from `https://`). CloudFront's `/ws` cache behavior (forward all headers, TTL=0) routes WebSocket to ALB transparently, allowing `wss://` everywhere.

---

## Security Architecture

| Layer | Control |
|-------|---------|
| Authentication | Cognito JWT (RS256) validated against JWKS on every WS connection |
| Authorization | API Gateway Cognito JWT authorizer on all Lambda routes |
| Image access | S3 keys validated: must start with `uploads/`, no path traversal |
| PII in logs | `PIIFilterHook` redacts phone numbers before CloudWatch |
| PII in DB | Vet phone stored as `+91XXXXX{last4}`; farmer phone stored unredacted for GSI but protected by DynamoDB encryption at rest |
| Content safety | Bedrock Guardrails (configurable via `ANTHROPIC_CUSTOM_HEADERS`) |
| Message limits | Chat: 2000 chars; symptom Q: 500 chars; symptom A: 1000 chars |
| Session memory | Max 40 history entries; per-session asyncio locks prevent race conditions |

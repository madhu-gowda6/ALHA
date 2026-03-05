# Project Overview

## ALHA — AI Livestock Health Assistant

ALHA is a bilingual (Hindi/English) AI-powered veterinary consultation system for Indian farmers. It enables farmers with limited veterinary access to diagnose livestock diseases, receive evidence-based treatment guidance, and connect with nearby veterinarians — all through a simple chat interface on their mobile browser.

---

## Problem Statement

Indian farmers — particularly smallholders in rural areas — often lack timely access to licensed veterinarians. Livestock diseases can spread rapidly, causing significant economic loss. Language barriers (Hindi vs. English) and low digital literacy further limit access to veterinary information.

---

## Solution

A Progressive Web App (PWA) accessible on any mobile browser, backed by a Claude AI agent that:

1. Conducts a structured symptom interview in the farmer's language
2. Requests and analyzes a photo of the affected animal
3. Classifies the disease using ML (Rekognition + Claude vision)
4. Retrieves evidence-based treatment from a veterinary knowledge base (ICAR/NDDB)
5. Assesses severity and coordinates with the nearest available vet via GPS + SMS

---

## Target Users

| User | Language | Interaction |
|------|----------|-------------|
| Indian farmers (smallholders) | Hindi or English (auto-detected) | Chat, voice, image upload |
| Veterinarians | — | Receive SMS with farmer location + case details |

### Demo Users

| Username | Language | Animal |
|----------|----------|--------|
| raju | Hindi | Cattle |
| savita | Hindi | Poultry |
| deepak | English | Buffalo |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Bilingual AI chat** | Auto-detects Hindi (Devanagari) or English. Strict language consistency per session. |
| **Voice input** | Speech-to-text in hi_IN / en_US via Web Speech API |
| **Structured symptom interview** | Claude generates targeted questions; farmer answers via an overlay form |
| **Image-based disease diagnosis** | Camera/gallery upload → AWS Rekognition Custom Labels + Claude vision double-check |
| **Bounding box visualization** | Highlights affected area on the uploaded photo |
| **Veterinary knowledge base** | Retrieves treatment protocols from ICAR/NDDB documents (Amazon Bedrock KB) |
| **Severity classification** | CRITICAL / HIGH / MEDIUM / LOW / NONE with color-coded badge |
| **GPS-based vet location** | Haversine nearest-vet search filtered by animal speciality |
| **SMS notifications** | Dual SMS via AWS SNS: farmer gets vet confirmation, vet gets location + case details |
| **Vet preference card** | For HIGH/MEDIUM severity, farmer chooses whether to contact the vet |
| **Consultation history** | Past consultations retrievable with treatment summary and KB citations |
| **Offline detection** | Bilingual offline screen on connectivity loss |
| **Medical disclaimer** | Mandatory disclaimer appended to every clinical response (enforced by system prompt) |

---

## Supported Animal Types

| Animal | Rekognition Model |
|--------|-----------------|
| Cattle | `rekognition_cattle_arn` |
| Poultry | `rekognition_poultry_arn` |
| Buffalo | Falls back to Claude vision (no dedicated model) |

---

## Supported Diseases

| Disease | Hindi Name | Severity |
|---------|-----------|----------|
| `lumpy_skin_disease` | लम्पी स्किन रोग | CRITICAL |
| `newcastle_disease` | रानीखेत रोग | CRITICAL |
| `anthrax` | एंथ्रेक्स (तिल्ली ज्वर) | CRITICAL |
| `foot_and_mouth_disease` | खुरपका-मुंहपका रोग | HIGH |
| `brucellosis` | ब्रुसेलोसिस | HIGH |
| `blackleg` | काला पांव | HIGH |
| Any other known disease | — | MEDIUM |
| Routine/preventive query | — | LOW |

---

## Monorepo Structure

```
ALHA/
├── alha/              ← Flutter PWA (web target)
│   └── lib/
│       ├── config/    ← App config, theme
│       ├── models/    ← Message, Consultation, Vet, WsMessage
│       ├── providers/ ← session, chat, camera (Riverpod)
│       ├── screens/   ← Chat, Login, History, Profile
│       ├── services/  ← WebSocket, Auth, Upload, Speech, Location
│       └── widgets/   ← TextBubble, ImageBubble, SeverityBadge, VetCard, overlays
│
├── alha-agent/        ← Claude Agent SDK service (ECS Fargate)
│   ├── app.py         ← FastAPI app, WebSocket endpoint, REST endpoints
│   ├── agent.py       ← Claude Agent SDK query loop + MCP server
│   ├── config.py      ← Environment variable config
│   ├── ws_map.py      ← Shared session→WebSocket map for tools
│   ├── hooks/         ← LoggingHook, PIIFilterHook
│   ├── models/        ← Consultation, Vet, WsMessages (Pydantic)
│   ├── tools/         ← 9 MCP tools (symptom_interview, classify_disease, ...)
│   ├── utils/         ← haversine, dynamo_helpers
│   └── prompts/       ← system_prompt.txt
│
├── alha-backend/      ← AWS SAM infrastructure + Lambda stubs
│   ├── template.yaml  ← Full AWS infrastructure definition
│   ├── functions/
│   │   ├── image_validator/    ← Lambda: POST /api/upload-url
│   │   ├── notification_handler/ ← Lambda: GET /api/history + POST /api/auth/login
│   │   └── disease_classifier/ ← Lambda stub (classification done in agent)
│   └── scripts/       ← seed_vets.py, create_demo_users.py, warm_rekognition.py
│
├── docs/              ← Project documentation (this directory)
├── .env               ← Environment variables (not committed)
└── .env.example       ← Template for .env
```

---

## Quick Links

- [System Architecture](02-architecture.md)
- [Technology Stack](03-technology-stack.md)
- [API Contracts (REST + WebSocket)](04-api-contracts.md)
- [Data Models](05-data-models.md)
- [Agent MCP Tools](06-agent-tools.md)
- [Flutter UI Components](07-flutter-ui-components.md)
- [Infrastructure (AWS SAM)](08-infrastructure.md)
- [Deployment Guide](09-deployment.md)

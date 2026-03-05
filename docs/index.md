# ALHA Project Documentation

**AI Livestock Health Assistant** — Bilingual (Hindi/English) AI veterinary consultation system for Indian farmers.

Generated: 2026-03-05 | Scan: Exhaustive | Mode: Initial Scan

---

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 1 | [Project Overview](01-project-overview.md) | Purpose, users, features, monorepo structure |
| 2 | [System Architecture](02-architecture.md) | Architecture diagram, consultation flow sequence, design decisions, security |
| 3 | [Technology Stack](03-technology-stack.md) | Tech stack table for all 3 parts with architecture patterns |
| 4 | [API Contracts](04-api-contracts.md) | REST endpoints + full WebSocket message protocol reference |
| 5 | [Data Models](05-data-models.md) | DynamoDB tables, Pydantic models, Dart models, in-memory session state |
| 6 | [Agent MCP Tools](06-agent-tools.md) | All 9 MCP tools, tool-calling sequences, PII handling |
| 7 | [Flutter UI Components](07-flutter-ui-components.md) | Screens, providers, services, widgets, navigation structure |
| 8 | [Infrastructure (AWS)](08-infrastructure.md) | SAM resources, IAM roles, environment variables, CloudWatch |
| 9 | [Deployment Guide](09-deployment.md) | Step-by-step deployment, local dev, monitoring, production checklist |

---

## Project Parts

| Part | Path | Type | Primary Tech |
|------|------|------|-------------|
| **alha** | `alha/` | Flutter PWA | Dart 3, Flutter Web, Riverpod, WebSocketChannel |
| **alha-agent** | `alha-agent/` | Python Backend | FastAPI, Claude Agent SDK, MCP, Bedrock |
| **alha-backend** | `alha-backend/` | AWS Infrastructure | SAM, Lambda, ECS Fargate, DynamoDB |

---

## Key Entry Points

| File | Purpose |
|------|---------|
| [alha/lib/main.dart](../alha/lib/main.dart) | Flutter app entry point |
| [alha/lib/screens/chat_screen.dart](../alha/lib/screens/chat_screen.dart) | Primary consultation UI |
| [alha-agent/app.py](../alha-agent/app.py) | FastAPI app + WebSocket endpoint |
| [alha-agent/agent.py](../alha-agent/agent.py) | Claude Agent SDK agentic loop |
| [alha-agent/prompts/system_prompt.txt](../alha-agent/prompts/system_prompt.txt) | Agent system prompt |
| [alha-backend/template.yaml](../alha-backend/template.yaml) | AWS SAM infrastructure |

---

## Scan Report

- **State file:** [project-scan-report.json](project-scan-report.json)
- **Files read:** All source files in `alha/lib/`, `alha-agent/`, `alha-backend/`
- **Excluded:** `.dart_tool/`, `.venv/`, `__pycache__/`, `.aws-sam/`, `build/`

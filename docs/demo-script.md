# ALHA Demo Script — Hackathon Presentation

**AI Livestock Health Assistant** | Demo Duration: ~4 minutes total

---

## Prerequisites (30 minutes before demo)

1. **Warm Rekognition models** (MUST run 30 min before demo):
   ```bash
   python scripts/warm_rekognition.py
   ```
   Wait until both models show `RUNNING` status. Note the ARNs printed.

2. **Seed demo vets** (idempotent — safe to re-run):
   ```bash
   python scripts/seed_vets.py
   ```

3. **Seed demo users** (idempotent):
   ```bash
   python scripts/create_demo_users.py
   ```
   Users created: `raju`, `savita`, `deepak` — all with password `Demo@1234`

4. **Verify ECS service is running** and FastAPI agent is healthy:
   ```
   GET https://<api-gateway-url>/health → {"status": "ok"}
   ```

5. **Open demo photos** (have ready to upload):
   - `demo_lsd_cattle.jpg` — Lumpy Skin Disease cattle photo
   - `demo_newcastle_poultry.jpg` — Newcastle Disease poultry photo

6. **Physical Android Chrome device** — ensure:
   - PWA installed from home screen (tap "Add to Home Screen")
   - Microphone permission granted
   - Camera permission granted

---

## Demo Scenario 1 — Raju (LSD Cattle, CRITICAL) — ≤90 seconds

**User:** `raju` / `Demo@1234` | **Language:** Hindi

### Steps

| Time | Action | Expected Result |
|------|--------|-----------------|
| 0:00 | Login as `raju` with password `Demo@1234` | Chat screen loads |
| 0:05 | Type (or speak in Hindi): **"Meri gaay ke upar daane aa gaye hain teen din se"** | Agent starts symptom interview |
| 0:10 | Answer cross-question 1: **"Haan, gaay ko bukhar bhi hai"** | Interview continues |
| 0:15 | Answer cross-question 2: **"Lagbhag 10 daane hain pair par bhi"** | Camera overlay appears |
| 0:20 | Upload `demo_lsd_cattle.jpg` via camera/gallery | Bounding box visible on image |
| 0:30 | (at 30s) Bounding box rendered on screen | ✅ Rekognition classified |
| 0:45 | (at 45s) Severity result shown: **"Lumpy Skin Disease — 89% confidence — CRITICAL"** | GPS request prompt appears |
| 0:50 | Allow GPS / share location | Vet search begins |
| 0:60 | (at 60s) Vet card shown with name, phone, distance | SNS SMS dispatching |
| 0:75 | (at 75s) Consultation saved — session_complete event | DynamoDB record visible in AWS Console |

**Verification:**
- AWS Console → DynamoDB → `alha-consultations` → scan → newest item shows `disease_name: lumpy_skin_disease`, `severity: CRITICAL`
- AWS Console → SNS → Text messaging → Published messages → delivery receipt within 30s

---

## Demo Scenario 2 — Savita (Newcastle Poultry, CRITICAL) — ≤90 seconds

**User:** `savita` / `Demo@1234` | **Language:** Hindi

### Steps

| Time | Action | Expected Result |
|------|--------|-----------------|
| 0:00 | Login as `savita` | Chat screen loads |
| 0:05 | Type: **"Meri murgiyan mar rahi hain teen raat mein"** | Agent starts symptom interview |
| 0:10 | Answer cross-question 1: **"Haan, naak se paani aa raha hai"** | Interview continues |
| 0:15 | Answer cross-question 2: **"Kaafi murgiyan ek saath beemar ho gayi"** | Camera overlay appears |
| 0:20 | Upload `demo_newcastle_poultry.jpg` | Poultry Rekognition model classifies |
| 0:45 | (at 45s) **"Newcastle Disease — CRITICAL"** shown | Poultry-specialist vet selected |
| 0:60 | (at 60s) Vet card shows a **poultry specialist** (not cattle vet) | SMS dispatched |
| 0:75 | Consultation saved | DynamoDB record visible |

**Verification:**
- Vet selected must have `speciality: poultry` in `alha-vets` table
- Confirm it is NOT a cattle-only vet

---

## Demo Scenario 3 — Deepak (Vaccination Query, LOW/NONE) — ≤30 seconds

**User:** `deepak` / `Demo@1234` | **Language:** English

### Steps

| Time | Action | Expected Result |
|------|--------|-----------------|
| 0:00 | Login as `deepak` | Chat screen loads |
| 0:05 | Type (English): **"When should I vaccinate my buffalo calf? She's 2 months old."** | Agent processes directly |
| 0:10 | (at 10s) No image request, no cross-questions | KB query triggered |
| 0:20 | (at 20s) ICAR-cited vaccination schedule returned in **English only** | Response displayed |
| 0:25 | (at 25s) Consultation saved, severity NONE/LOW | No vet dispatched, no SMS |

**Verification:**
- Response is entirely in English
- No camera overlay appears
- No vet card shown
- DynamoDB record: `severity: LOW` or `NONE`, `vet_assigned: none`

---

## Physical Android Chrome Verification Checklist

Before demo, confirm on the physical device:

- [ ] **Camera capture** — tap camera icon, take photo without Chrome DevTools
- [ ] **Voice input** — tap microphone, speak Hindi phrase, text appears in input bar
- [ ] **PWA install** — browser shows "Add to Home Screen" banner, app icon on home screen
- [ ] **PWA launch** — open from home screen icon, splash screen loads, no browser chrome
- [ ] **Offline shell** — disable WiFi, open PWA → app shell loads (not blank page) → bilingual "इंटरनेट कनेक्शन नहीं है / No internet connection" shown

---

## Consultation History Demo

After completing any scenario:

1. Tap the **History icon** (clock icon in top-right of ChatScreen)
2. `HistoryScreen` loads showing past consultations
3. Each row shows: animal icon, disease name, severity badge, timestamp
4. Tap any row → detail view with full record (confidence %, vet, treatment, citations)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Rekognition returns no results | Run `warm_rekognition.py` — model must be `RUNNING` |
| SNS SMS not delivered | Check SNS sandbox — add destination phone to sandbox verified numbers |
| WebSocket disconnects mid-flow | Check ECS task is running; refresh page — reconnect logic retries |
| History shows "No consultations" | Ensure `farmer_phone` is stored unredacted (Story 5.1 fix applied) |
| Vet not found | Run `seed_vets.py` — ensure vets are in `alha-vets` DynamoDB table |
| Camera not working on Android | Ensure HTTPS (not HTTP) — camera API requires secure context |

---

## Judge Talking Points

### Architecture Highlights
- **Serverless + ECS hybrid**: API Gateway → Lambda (auth, history) + ECS (AI agent WebSocket)
- **Bedrock Knowledge Base**: ICAR livestock guides indexed with vector embeddings
- **Rekognition Custom Labels**: Two fine-tuned models (cattle, poultry) with bounding boxes
- **Real-time WebSocket**: Agentic multi-turn conversation with sub-second streaming

### AWS Services Used
`Cognito` · `API Gateway (HTTP API v2)` · `Lambda` · `ECS Fargate` · `Rekognition Custom Labels` · `Bedrock (Claude + Knowledge Base)` · `DynamoDB (GSI)` · `S3` · `SNS SMS` · `CloudWatch`

### Key Differentiators
- **Bilingual (Hindi + English)** — farmers speak in Hindi, app responds appropriately
- **PII redaction in logs** — farmer phone numbers redacted in CloudWatch via PostToolUse hook
- **PWA** — works on any Android Chrome, no app store required, offline shell support
- **Sub-90s end-to-end** — from symptom description to vet SMS in under 90 seconds

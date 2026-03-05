# API Contracts

## REST Endpoints

All REST endpoints are served by the `alha-agent` FastAPI service (via ALB/API Gateway) or stub Lambda functions.

### Base URL

| Environment | Base URL |
|-------------|----------|
| Production (API GW) | `https://{api-gw-id}.execute-api.us-east-1.amazonaws.com/prod` |
| Agent direct (ALB) | `http://alha-alb-xxxx.us-east-1.elb.amazonaws.com` |
| CloudFront HTTPS | `https://{cf-domain}.cloudfront.net` |

---

### `POST /api/auth/login`

Authenticate farmer with Cognito USER_PASSWORD_AUTH flow.

**Auth:** None (public)

**Request Body:**
```json
{
  "username": "raju",
  "password": "password123"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "token": "<cognito-id-token-jwt>",
    "username": "raju"
  },
  "error": null
}
```

**Response 401:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_FAILED",
    "message": "Invalid credentials",
    "message_hi": "गलत उपयोगकर्ता नाम या पासवर्ड"
  }
}
```

**Implemented in:** `alha-agent/app.py` (primary), `alha-backend/functions/notification_handler/app.py::auth_handler` (Lambda stub)

---

### `POST /api/upload-url`

Generate a pre-signed S3 PUT URL for image upload.

**Auth:** `Authorization: Bearer <cognito-id-token>`

**Request Body:**
```json
{ "session_id": "uuid-v4" }
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "upload_url": "https://s3.amazonaws.com/alha-images/uploads/...",
    "s3_key": "uploads/{session_id}/{uuid}.jpg"
  },
  "error": null
}
```

**S3 key format:** `uploads/{session_id}/{uuid}.jpg`
**Expiry:** 15 minutes
**Content-Type:** `image/jpeg` (enforced)

**Implemented in:** `alha-agent/app.py`, `alha-backend/functions/image_validator/app.py`

---

### `GET /api/history`

Retrieve past consultations for the authenticated farmer.

**Auth:** `Authorization: Bearer <cognito-id-token>`

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "consultation_id": "uuid",
      "animal_type": "cattle",
      "disease_name": "lumpy_skin_disease",
      "confidence_score": 87.5,
      "severity": "CRITICAL",
      "vet_assigned": "Dr. Ramesh Kumar",
      "treatment_summary": "...",
      "kb_citations": "[\"source1\", \"source2\"]",
      "timestamp": "2026-03-05T10:30:00Z"
    }
  ],
  "error": null
}
```

**Implemented in:** `alha-agent/app.py`, `alha-backend/functions/notification_handler/app.py::handler`
**DynamoDB GSI:** `gsi-farmer-phone` on `alha-consultations` table; sorted by `timestamp` descending in application.

---

### `GET /health`

Health check for ALB target group.

**Auth:** None

**Response 200:** `{"status": "ok"}`

---

### `GET /debug/claude` _(Development only)_

Probe Claude subprocess binary. Remove before production.

---

## WebSocket Protocol

**URL:** `wss://{host}/ws?token={cognito-id-token}`

Authentication is via `token` query parameter (Cognito JWT). The agent validates the JWT against Cognito JWKS on connection before `accept()`.

**Close codes:**
- `4001` — Authentication required or invalid token
- `4002` — Authentication service unavailable

---

### Client → Agent Messages

#### `chat` — Farmer sends a text message
```json
{
  "type": "chat",
  "session_id": "uuid-v4",
  "message": "मेरी गाय को बुखार है",
  "language": "hi"
}
```
- `language`: `"hi"` or `"en"` (auto-detected by Flutter from Devanagari Unicode)
- Max message length: 2000 characters

---

#### `symptom_answers` — Farmer completes symptom interview
```json
{
  "type": "symptom_answers",
  "session_id": "uuid-v4",
  "answers": [
    { "question": "How long has the fever lasted?", "answer": "3 days" },
    { "question": "Are there skin bumps?", "answer": "Yes, many" }
  ]
}
```
- Max 10 answers; each question capped at 500 chars, answer at 1000 chars.

---

#### `image_data` — Flutter notifies agent of uploaded image
```json
{
  "type": "image_data",
  "session_id": "uuid-v4",
  "s3_key": "uploads/{session_id}/{uuid}.jpg"
}
```
- Validated: must start with `uploads/`, no `..` traversal, max 500 chars.

---

#### `gps_data` — Farmer shares GPS coordinates
```json
{
  "type": "gps_data",
  "session_id": "uuid-v4",
  "lat": 28.6139,
  "lon": 77.2090
}
```

---

#### `vet_preference` — Farmer responds to vet connection offer
```json
{
  "type": "vet_preference",
  "session_id": "uuid-v4",
  "choice": "yes"
}
```
- `choice`: `"yes"` or `"no"`

---

### Agent → Client Messages

#### `token` — Streaming text chunk
```json
{
  "type": "token",
  "session_id": "uuid-v4",
  "text": "आपकी गाय को "
}
```

#### `response_complete` — Agent turn finished
```json
{
  "type": "response_complete",
  "session_id": "uuid-v4"
}
```

#### `error` — Bilingual error
```json
{
  "type": "error",
  "session_id": "uuid-v4",
  "message": "An error occurred processing your request.",
  "message_hi": "आपका अनुरोध प्रसंस्करण करते समय एक त्रुटि हुई।"
}
```

#### `frontend_action: symptom_interview` — Show symptom overlay
```json
{
  "type": "frontend_action",
  "action": "symptom_interview",
  "session_id": "uuid-v4",
  "questions": ["How long has the fever lasted?", "Are there skin bumps?"],
  "questions_hi": ["बुखार कितने दिनों से है?", "क्या त्वचा पर गांठें हैं?"]
}
```

#### `frontend_action: request_image` — Show camera overlay
```json
{
  "type": "frontend_action",
  "action": "request_image",
  "session_id": "uuid-v4",
  "prompt": "Please take a photo of the affected area",
  "prompt_hi": "कृपया प्रभावित क्षेत्र की फोटो लें"
}
```

#### `frontend_action: request_gps` — Request location permission
```json
{
  "type": "frontend_action",
  "action": "request_gps",
  "session_id": "uuid-v4",
  "prompt_text": "Please share your location to find the nearest vet.",
  "prompt_text_hi": "निकटतम पशु चिकित्सक खोजने के लिए कृपया अपना स्थान साझा करें।"
}
```

#### `diagnosis` — Disease classification result
```json
{
  "type": "diagnosis",
  "session_id": "uuid-v4",
  "soft_failure": false,
  "disease": "lumpy_skin_disease",
  "confidence": 87.5,
  "bbox": { "left": 0.2, "top": 0.3, "width": 0.4, "height": 0.3 },
  "s3_key": "uploads/...",
  "message": null,
  "message_hi": null
}
```
- `soft_failure: true` when image is unclear — Flutter retriggers camera overlay automatically.
- `bbox`: normalized coordinates (0–1) for bounding box overlay on image.

#### `severity` — Severity badge event
```json
{
  "type": "severity",
  "level": "CRITICAL",
  "session_id": "uuid-v4"
}
```
- `level`: `CRITICAL` | `HIGH` | `MEDIUM` | `LOW` | `NONE`

#### `vet_found` — Nearest vet located
```json
{
  "type": "vet_found",
  "name": "Dr. Ramesh Kumar",
  "speciality": "cattle",
  "distance_km": 4.7,
  "phone": "+919876543210",
  "session_id": "uuid-v4"
}
```

#### `notification_sent` — SMS dispatched
```json
{
  "type": "notification_sent",
  "vet_name": "Dr. Ramesh Kumar",
  "session_id": "uuid-v4"
}
```

#### `session_complete` — Consultation persisted
```json
{
  "type": "session_complete",
  "consultation_id": "uuid-v4",
  "session_id": "uuid-v4"
}
```
